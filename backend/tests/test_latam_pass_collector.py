import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import campaigns as campaigns_api
from app.collectors.latam_pass import LatamPassCollector
from app.core.database import Base, get_db
from app.models.campaign import Campaign
from app.models.campaign_snapshot import CampaignSnapshot


LATAM_PASS_FIXTURE = """
<!doctype html>
<html><body>
  <article>
    <h2>Transfira pontos Esfera e ganhe 30% de bônus em Milhas LATAM Pass</h2>
    <p>Cadastre-se na promoção entre 25/07/2026 e 26/07/2026.</p>
    <p>Clientes Clube LATAM Pass são elegíveis. Bonificação limitada a
       300.000 milhas e creditada em até 10 dias úteis.</p>
    <a href="/pt_br/promocao/esfera-milhas-extras">Conferir oferta</a>
  </article>
  <article>
    <h2>Compre milhas com até 63% de desconto</h2>
    <p>Válido até 30/07/2026 para membros LATAM Pass elegíveis.</p>
    <a href="https://latampass.latam.com/pt_br/oferta/compra-milhas-julho">
      Conferir oferta
    </a>
  </article>
</body></html>
"""


def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _client():
    def handler(request):
        return httpx.Response(
            200,
            text=LATAM_PASS_FIXTURE,
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_latam_pass_parses_bonus_partner_dates_and_eligibility():
    campaigns = LatamPassCollector().parse(LATAM_PASS_FIXTURE)
    transfer = campaigns[0]

    assert len(campaigns) == 2
    assert transfer.company == "LATAM Pass"
    assert transfer.program_name == "LATAM Pass"
    assert transfer.campaign_type.value == "transfer_bonus"
    assert transfer.partner_name == "Esfera"
    assert transfer.start_date.isoformat() == "2026-07-25"
    assert transfer.end_date.isoformat() == "2026-07-26"
    assert "bonus_percent=30" in transfer.extraction_notes
    assert "registration_required=true" in transfer.extraction_notes
    assert "club_latam_pass_mentioned=true" in transfer.extraction_notes
    assert "credit_deadline=" in transfer.extraction_notes
    assert "cpf_limit=300.000 milhas" in transfer.extraction_notes


def test_latam_pass_purchase_keeps_unknown_cost_and_end_date():
    purchase = LatamPassCollector().parse(LATAM_PASS_FIXTURE)[1]

    assert purchase.campaign_type.value == "points_purchase"
    assert purchase.end_date.isoformat() == "2026-07-30"
    assert purchase.cost_brl is None
    assert purchase.cost_status.value == "unknown"


def test_latam_pass_deduplication_history_and_intelligence_integration():
    engine = _engine()
    collector = LatamPassCollector()
    with Session(engine) as db, _client() as client:
        first = collector.run(db, client=client)
    with Session(engine) as db, _client() as client:
        second = collector.run(db, client=client)
        campaigns = list(db.scalars(select(Campaign)))
        snapshots = db.scalar(select(func.count()).select_from(CampaignSnapshot))

    assert first.source == "LATAM Pass"
    assert first.inserted == 2
    assert second.unchanged == 2
    assert len(campaigns) == 2
    assert snapshots == 2
    assert all(item.analysis_status == "preliminary" for item in first.campaigns)
    assert all(item.cpm is None for item in campaigns)


def test_latam_pass_endpoint_returns_standardized_result(monkeypatch):
    engine = _engine()
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app = FastAPI()
    app.include_router(campaigns_api.router, prefix="/api")

    def override_get_db():
        with testing_session() as db:
            yield db

    collector = LatamPassCollector()
    monkeypatch.setattr(collector, "fetch", lambda **kwargs: LATAM_PASS_FIXTURE)
    monkeypatch.setattr(campaigns_api, "get_collector", lambda source: collector)
    app.dependency_overrides[get_db] = override_get_db

    response = TestClient(app).post("/api/campaigns/scan/latam-pass")
    payload = response.json()
    assert response.status_code == 200
    assert payload["source"] == "LATAM Pass"
    assert payload["inserted"] == 2
    assert payload["campaigns"][0]["attention_required"] is not None
