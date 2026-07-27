from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.campaigns import router
from app.core.database import Base, get_db


def _build_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    app = FastAPI()
    app.include_router(router, prefix="/api")

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_get_campaign_by_id_and_raw_payload():
    client = _build_client()
    created = client.post(
        "/api/campaigns",
        json={
            "company": "Livelo",
            "title": "[UPGRADE] Top - 96k pontos em 12 meses - anual",
            "source_url": "https://assets.example.com/top.pdf",
        },
    )
    assert created.status_code == 201
    campaign = created.json()

    response = client.get(f"/api/campaigns/{campaign['id']}")
    assert response.status_code == 200
    assert response.json()["campaign_key"] == campaign["campaign_key"]
    assert response.json()["cost_status"] == "unknown"

    raw_response = client.get(f"/api/campaigns/{campaign['id']}/raw")
    assert raw_response.status_code == 200
    assert raw_response.json()["raw"]["title"].startswith("[UPGRADE]")


def test_different_campaigns_from_same_page_are_not_duplicates():
    client = _build_client()
    common = {"company": "Livelo", "source_url": "https://assets.example.com/shared.pdf"}
    first = client.post("/api/campaigns", json={**common, "title": "Upgrade Top 96k pontos"})
    second = client.post("/api/campaigns", json={**common, "title": "Adesão Mega 74k pontos"})
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["campaign_key"] != second.json()["campaign_key"]


def test_scan_response_contains_normalized_fields_and_action():
    client = _build_client()
    response = client.post("/api/campaigns/scan-demo")
    assert response.status_code == 200
    campaign = response.json()["campaigns"][0]
    assert {
        "id",
        "campaign_key",
        "title",
        "normalized_title",
        "campaign_type",
        "modality",
        "bonus_points",
        "duration_months",
        "monthly_points",
        "cost_status",
        "extraction_confidence",
        "action",
    }.issubset(campaign)
    assert campaign["action"] == "inserted"
