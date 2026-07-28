import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import campaigns as campaigns_api
from app.collectors.base import BaseCollector, CollectorError
from app.collectors.esfera import EsferaCollector
from app.collectors.livelo import LiveloCollector
from app.core.database import Base, get_db
from app.models.campaign import Campaign
from app.models.campaign_snapshot import CampaignSnapshot


ESFERA_FIXTURE = """
<!doctype html>
<html><body>
  <h2 data-partner="Banco Exemplo">Transferência bonificada: ganhe 80% de bônus</h2>
  <p>Cadastre-se e transfira entre 25/07/2026 e 28/07/2026.</p>
  <a href="/regulamentos/banco-exemplo.pdf">Consulte o regulamento</a>
  <h3>Compra de pontos: até 50 mil pontos</h3>
  <p>Oferta válida de 26/07/2026 a 30/07/2026 para clientes elegíveis.</p>
  <a href="https://www.esfera.com.vc/regulamentos/compra.pdf">Regulamento</a>
</body></html>
"""


class FixtureCollector(BaseCollector):
    source_name = "Fixture"
    source_url = "https://official.example/campaigns"

    def parse(self, html):
        return []


def _http_client(*, body=ESFERA_FIXTURE, status=200, headers=None):
    def handler(request):
        return httpx.Response(
            status,
            text=body,
            headers=headers or {"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def test_base_collector_validates_http_size_and_html():
    collector = FixtureCollector()
    with _http_client(status=503) as client:
        with pytest.raises(CollectorError, match="HTTP 503"):
            collector.fetch(client=client)

    collector.max_response_bytes = 20
    with _http_client() as client:
        with pytest.raises(CollectorError, match="limite"):
            collector.fetch(client=client)

    collector.max_response_bytes = 5_000_000
    with _http_client(body='{"items":[]}', headers={"content-type": "application/json"}) as client:
        with pytest.raises(CollectorError, match="inesperado"):
            collector.fetch(client=client)


def test_livelo_adapter_preserves_existing_parser():
    fixture = """
    <html><body><h2>[COMPRA DE PONTOS] 52% OFF</h2>
    <p>Período 24/07/2026 - 26/07/2026</p>
    <a href="/regulamento/compra-pontos">Regulamento</a></body></html>
    """
    campaigns = LiveloCollector().parse(fixture)
    assert len(campaigns) == 1
    assert campaigns[0].company == "Livelo"


def test_esfera_parses_official_fixture_without_inventing_cost():
    campaigns = EsferaCollector().parse(ESFERA_FIXTURE)
    assert len(campaigns) == 2
    assert campaigns[0].company == "Esfera"
    assert campaigns[0].program_name == "Esfera"
    assert campaigns[0].partner_name == "Banco Exemplo"
    assert campaigns[0].regulation_url.endswith("banco-exemplo.pdf")
    assert campaigns[0].cost_brl is None
    assert campaigns[0].cost_status.value == "unknown"


def test_esfera_run_deduplicates_and_integrates_history_and_intelligence():
    engine = _engine()
    collector = EsferaCollector()
    with Session(engine) as db, _http_client() as client:
        first = collector.run(db, client=client)
    with Session(engine) as db, _http_client() as client:
        second = collector.run(db, client=client)
        campaigns = list(db.scalars(select(Campaign)))
        snapshots = db.scalar(select(func.count()).select_from(CampaignSnapshot))

    assert first.source == "Esfera"
    assert first.inserted == 2
    assert second.unchanged == 2
    assert len(campaigns) == 2
    assert snapshots == 2
    assert all(item.analysis_status == "preliminary" for item in first.campaigns)
    assert all(item.cpm is None for item in campaigns)


def test_esfera_endpoint_returns_standardized_source_result(monkeypatch):
    engine = _engine()
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app = FastAPI()
    app.include_router(campaigns_api.router, prefix="/api")

    def override_get_db():
        with testing_session() as db:
            yield db

    collector = EsferaCollector()
    monkeypatch.setattr(collector, "fetch", lambda **kwargs: ESFERA_FIXTURE)
    monkeypatch.setattr(campaigns_api, "get_collector", lambda source: collector)
    app.dependency_overrides[get_db] = override_get_db

    response = TestClient(app).post("/api/campaigns/scan/esfera")
    payload = response.json()
    assert response.status_code == 200
    assert payload["source"] == "Esfera"
    assert payload["inserted"] == 2
    assert {
        "id",
        "campaign_key",
        "title",
        "action",
        "change_type",
        "analysis_status",
        "recommendation_level",
        "confidence_level",
        "attention_required",
    }.issubset(payload["campaigns"][0])
