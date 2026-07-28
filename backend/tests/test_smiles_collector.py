import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import campaigns as campaigns_api
from app.collectors.smiles import SmilesCollector
from app.core.database import Base, get_db
from app.models.campaign import Campaign
from app.models.campaign_snapshot import CampaignSnapshot


SMILES_FIXTURE = """
<!doctype html>
<html><body>
  <article>
    <h2>Transferência de Pontos Itaú: ganhe até 70% de bônus</h2>
    <p>Cadastre-se nesta promoção entre 13/07/2026 e 14/07/2026.</p>
    <p>Assinantes Clube Smiles recebem o bônus máximo. Bonificação limitada a
       300.000 milhas por CPF e creditada em até 10 dias úteis.</p>
    <a href="/portal/campanhas/bancos-itau-07-2026">Ver regulamento</a>
  </article>
  <article>
    <h2>Assine o Clube Smiles e ganhe 12 mil milhas</h2>
    <p>Oferta para novas adesões de 15/07/2026 a 20/07/2026.</p>
    <a href="https://www.smiles.com.br/campanhas/clube-smiles-julho">
      Confira a campanha
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
            text=SMILES_FIXTURE,
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_smiles_parses_transfer_bonus_partner_dates_and_registration():
    campaigns = SmilesCollector().parse(SMILES_FIXTURE)
    transfer = campaigns[0]

    assert len(campaigns) == 2
    assert transfer.company == "Smiles"
    assert transfer.program_name == "Smiles"
    assert transfer.campaign_type.value == "transfer_bonus"
    assert transfer.partner_name == "Itaú"
    assert transfer.start_date.isoformat() == "2026-07-13"
    assert transfer.end_date.isoformat() == "2026-07-14"
    assert "bonus_percent=70" in transfer.extraction_notes
    assert "registration_required=true" in transfer.extraction_notes
    assert "credit_deadline=" in transfer.extraction_notes
    assert "cpf_limit=300.000 milhas" in transfer.extraction_notes


def test_smiles_parses_club_fixture_without_inventing_cost():
    club = SmilesCollector().parse(SMILES_FIXTURE)[1]

    assert club.campaign_type.value == "subscription"
    assert club.cost_brl is None
    assert club.cost_status.value == "unknown"
    assert "club_smiles_mentioned=true" in club.extraction_notes


def test_smiles_deduplication_history_and_intelligence_integration():
    engine = _engine()
    collector = SmilesCollector()
    with Session(engine) as db, _client() as client:
        first = collector.run(db, client=client)
    with Session(engine) as db, _client() as client:
        second = collector.run(db, client=client)
        campaigns = list(db.scalars(select(Campaign)))
        snapshots = db.scalar(select(func.count()).select_from(CampaignSnapshot))

    assert first.source == "Smiles"
    assert first.inserted == 2
    assert second.unchanged == 2
    assert len(campaigns) == 2
    assert snapshots == 2
    assert all(item.analysis_status == "preliminary" for item in first.campaigns)
    assert all(item.cpm is None for item in campaigns)


def test_smiles_endpoint_returns_standardized_result(monkeypatch):
    engine = _engine()
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app = FastAPI()
    app.include_router(campaigns_api.router, prefix="/api")

    def override_get_db():
        with testing_session() as db:
            yield db

    collector = SmilesCollector()
    monkeypatch.setattr(collector, "fetch", lambda **kwargs: SMILES_FIXTURE)
    monkeypatch.setattr(campaigns_api, "get_collector", lambda source: collector)
    app.dependency_overrides[get_db] = override_get_db

    response = TestClient(app).post("/api/campaigns/scan/smiles")
    payload = response.json()
    assert response.status_code == 200
    assert payload["source"] == "Smiles"
    assert payload["inserted"] == 2
    assert payload["campaigns"][0]["recommendation_level"]
