from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.campaigns import router as campaigns_router
from app.api.intelligence import router as intelligence_router
from app.core.database import Base, get_db


def _client():
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
    return TestClient(app)


def _create(client, *, company, program_name, title, bonus_points):
    response = client.post(
        "/api/campaigns",
        json={
            "company": company,
            "program_name": program_name,
            "title": title,
            "source_url": f"https://official.example/{company}",
            "bonus_points": bonus_points,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_dashboard_returns_best_ranking_history_update_and_programs():
    client = _client()
    first = _create(
        client,
        company="Livelo",
        program_name="Clube Livelo",
        title="Campanha 30 mil pontos",
        bonus_points=30_000,
    )
    second = _create(
        client,
        company="Smiles",
        program_name="Smiles",
        title="Campanha 70 mil pontos",
        bonus_points=70_000,
    )

    response = client.get("/api/intelligence/dashboard")
    payload = response.json()

    assert response.status_code == 200
    assert payload["best_campaign_today"]["campaign"]["id"] in {first["id"], second["id"]}
    assert len(payload["ranking"]) == 2
    assert payload["ranking"][0]["campaign"]["hc_score"] >= payload["ranking"][1]["campaign"]["hc_score"]
    assert len(payload["recent_history"]) == 2
    assert payload["last_updated_at"]
    assert payload["programs"] == ["Clube Livelo", "Smiles"]


def test_dashboard_program_filter_limits_ranking_and_history():
    client = _client()
    _create(
        client,
        company="Livelo",
        program_name="Clube Livelo",
        title="Campanha Livelo",
        bonus_points=20_000,
    )
    _create(
        client,
        company="Smiles",
        program_name="Smiles",
        title="Campanha Smiles",
        bonus_points=40_000,
    )

    response = client.get("/api/intelligence/dashboard", params={"program": "Smiles"})
    payload = response.json()

    assert response.status_code == 200
    assert len(payload["ranking"]) == 1
    assert payload["ranking"][0]["campaign"]["program_name"] == "Smiles"
    assert len(payload["recent_history"]) == 1
    assert payload["recent_history"][0]["program_name"] == "Smiles"
