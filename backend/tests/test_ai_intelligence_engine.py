from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.campaigns import router as campaigns_router
from app.api.intelligence import router as intelligence_router
from app.core.database import Base, get_db
from app.models.campaign import Campaign
from app.services.ai_intelligence_engine import CampaignInsightEngine


def _setup():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app = FastAPI()
    app.include_router(campaigns_router, prefix="/api")
    app.include_router(intelligence_router, prefix="/api")

    def override_get_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), testing_session


def _create(
    client,
    *,
    title,
    points,
    cost=None,
    cost_status="unknown",
    company="Livelo",
):
    response = client.post(
        "/api/campaigns",
        json={
            "company": company,
            "program_name": company,
            "campaign_type": "transfer_bonus",
            "title": title,
            "source_url": f"https://official.example/{title}",
            "bonus_points": points,
            "cost_brl": cost,
            "cost_status": cost_status,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_ai_analysis_summarizes_explains_and_compares_without_external_llm():
    client, _ = _setup()
    _create(client, title="Campanha comparável", points=30_000)
    current = _create(client, title="Campanha principal", points=60_000)

    response = client.get(f"/api/intelligence/{current['id']}/ai-analysis")
    payload = response.json()

    assert response.status_code == 200
    assert payload["engine"] == "deterministic-ai-ready-v1"
    assert "Campanha principal" in payload["automatic_summary"]
    assert "HC Score" in payload["automatic_summary"]
    assert len(payload["hc_score_explanation"]) >= 3
    assert payload["recommendation_label"] in {
        "Aguarde",
        "Promoção acima da média",
    }
    assert len(payload["similar_campaigns"]) == 1
    assert payload["similar_campaigns"][0]["title"] == "Campanha comparável"
    assert payload["forecast_status"] == "not_configured"
    assert "regras determinísticas" in payload["forecast_message"]


def test_known_attractive_campaign_can_receive_worth_considering_recommendation():
    client, _ = _setup()
    _create(
        client,
        title="Referência conhecida",
        points=20_000,
        cost=1_000,
        cost_status="known",
    )
    current = _create(
        client,
        title="Oferta conhecida superior",
        points=50_000,
        cost=500,
        cost_status="known",
    )

    payload = client.get(f"/api/intelligence/{current['id']}/ai-analysis").json()

    assert payload["recommendation_code"] == "worth_considering"
    assert payload["recommendation_label"] == "Vale aproveitar"
    assert any("70% de valor por CPM" in reason for reason in payload["hc_score_explanation"])


def test_prediction_provider_extension_point_can_be_replaced():
    client, testing_session = _setup()
    created = _create(client, title="Campanha futura", points=10_000)

    class FakePredictionProvider:
        def predict(self, campaign, peers):
            return "ready", "Previsão de teste disponível."

    with testing_session() as db:
        campaign = db.get(Campaign, created["id"])
        analysis = CampaignInsightEngine(FakePredictionProvider()).analyze(db, campaign)

    assert analysis.forecast_status == "ready"
    assert analysis.forecast_message == "Previsão de teste disponível."


def test_ai_analysis_returns_404_for_unknown_campaign():
    client, _ = _setup()
    response = client.get("/api/intelligence/999/ai-analysis")
    assert response.status_code == 404
