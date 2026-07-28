import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import campaigns as campaigns_api
from app.collectors.azul_fidelidade import AzulFidelidadeCollector
from app.collectors.base import CollectorError
from app.core.database import Base, get_db
from app.models.campaign import Campaign
from app.models.campaign_snapshot import CampaignSnapshot
from app.schemas.campaign import CollectorScanResult


AZUL_FIXTURE = """
<!doctype html>
<html><body>
  <article>
    <h2>Transfira pontos Livelo e ganhe 100% de bônus no Azul Fidelidade</h2>
    <p>Cadastre-se entre 25/07/2026 e 27/07/2026.</p>
    <p>Clientes Clube Azul são elegíveis. Bonificação limitada a 300.000 pontos
       e creditada em até 10 dias úteis.</p>
    <a href="/br/pt/ofertas/pontos/livelo-bonus-julho">Acessar regulamento</a>
  </article>
  <article>
    <h2>Cartão Azul Itaú: Clube Azul 2026 com 80 mil pontos bônus</h2>
    <p>Válido até 31/07/2026 para clientes que atingirem a meta de gastos.</p>
    <a href="https://www.voeazul.com.br/br/pt/ofertas/regulamento-cartao-azul-itau">
      Ver campanha
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


def _http_client():
    def handler(request):
        return httpx.Response(
            200,
            text=AZUL_FIXTURE,
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def _api_client():
    engine = _engine()
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app = FastAPI()
    app.include_router(campaigns_api.router, prefix="/api")

    def override_get_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_azul_parses_bonus_partner_dates_eligibility_and_club():
    campaigns = AzulFidelidadeCollector().parse(AZUL_FIXTURE)
    transfer = campaigns[0]

    assert len(campaigns) == 2
    assert transfer.company == "Azul Fidelidade"
    assert transfer.program_name == "Azul Fidelidade"
    assert transfer.campaign_type.value == "transfer_bonus"
    assert transfer.partner_name == "Livelo"
    assert transfer.start_date.isoformat() == "2026-07-25"
    assert transfer.end_date.isoformat() == "2026-07-27"
    assert "bonus_percent=100" in transfer.extraction_notes
    assert "registration_required=true" in transfer.extraction_notes
    assert "clube_azul_mentioned=true" in transfer.extraction_notes
    assert "credit_deadline=" in transfer.extraction_notes
    assert "cpf_limit=300.000 pontos" in transfer.extraction_notes


def test_azul_card_campaign_extracts_points_and_keeps_unknown_cost():
    collector = AzulFidelidadeCollector()
    card = collector.normalize(collector.parse(AZUL_FIXTURE)[1])

    assert card.campaign_type.value == "card_acquisition"
    assert card.bonus_points == 80_000
    assert card.end_date.isoformat() == "2026-07-31"
    assert card.cost_brl is None
    assert card.cost_status.value == "unknown"


def test_azul_deduplication_history_and_intelligence_integration():
    engine = _engine()
    collector = AzulFidelidadeCollector()
    with Session(engine) as db, _http_client() as client:
        first = collector.run(db, client=client)
    with Session(engine) as db, _http_client() as client:
        second = collector.run(db, client=client)
        campaigns = list(db.scalars(select(Campaign)))
        snapshots = db.scalar(select(func.count()).select_from(CampaignSnapshot))

    assert first.source == "Azul Fidelidade"
    assert first.inserted == 2
    assert second.unchanged == 2
    assert len(campaigns) == 2
    assert snapshots == 2
    assert all(item.analysis_status == "preliminary" for item in first.campaigns)
    assert all(item.cpm is None for item in campaigns)


def test_azul_endpoint_returns_standardized_result(monkeypatch):
    client = _api_client()
    collector = AzulFidelidadeCollector()
    monkeypatch.setattr(collector, "fetch", lambda **kwargs: AZUL_FIXTURE)
    monkeypatch.setattr(campaigns_api, "get_collector", lambda source: collector)

    response = client.post("/api/campaigns/scan/azul-fidelidade")
    payload = response.json()
    assert response.status_code == 200
    assert payload["source"] == "Azul Fidelidade"
    assert payload["inserted"] == 2


def test_scan_all_continues_after_one_source_failure(monkeypatch):
    client = _api_client()
    calls = []

    class FakeCollector:
        def __init__(self, source_name, fails=False):
            self.source_name = source_name
            self.fails = fails

        def run(self, db):
            calls.append(self.source_name)
            if self.fails:
                raise CollectorError(f"Falha controlada em {self.source_name}.")
            return CollectorScanResult(
                source=self.source_name,
                analyzed=1,
                inserted=0,
                updated=0,
                unchanged=1,
                errors=0,
                duplicates=1,
                campaigns=[],
            )

    collectors = {
        "livelo": FakeCollector("Livelo"),
        "esfera": FakeCollector("Esfera", fails=True),
        "smiles": FakeCollector("Smiles"),
        "latam-pass": FakeCollector("LATAM Pass"),
        "azul-fidelidade": FakeCollector("Azul Fidelidade"),
    }
    monkeypatch.setattr(campaigns_api, "get_collector", lambda source: collectors[source])

    response = client.post("/api/campaigns/scan/all")
    payload = response.json()
    assert response.status_code == 200
    assert calls == ["Livelo", "Esfera", "Smiles", "LATAM Pass", "Azul Fidelidade"]
    assert payload["analyzed"] == 4
    assert payload["unchanged"] == 4
    assert payload["errors"] == 1
    assert len(payload["sources"]) == 5
    assert payload["sources"][1]["status"] == "error"
    assert payload["sources"][4]["status"] == "success"
