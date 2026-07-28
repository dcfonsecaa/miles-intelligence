from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import campaigns as campaigns_api
from app.api.scanner import build_global_ranking, router
from app.core.database import Base, get_db
from app.schemas.campaign import CollectorScanResult, ScanCampaignRead


def _campaign(*, campaign_key, title, company, hc_score):
    return ScanCampaignRead(
        id=1,
        company=company,
        title=title,
        source_url="https://official.example/campaign",
        campaign_key=campaign_key,
        cpm=None,
        hc_score=hc_score,
        anomaly_score=0,
        detected_at="2026-07-28T12:00:00",
        updated_at="2026-07-28T12:00:00",
        action="inserted",
        change_type="created",
        analysis_status="preliminary",
        recommendation_level="monitor",
        confidence_level="low",
        attention_required=False,
    )


def test_global_ranking_is_unique_and_ordered_by_hc_score():
    lower = _campaign(campaign_key="a", title="Oferta A", company="Livelo", hc_score=30)
    higher_duplicate = lower.model_copy(update={"hc_score": 55})
    second = _campaign(campaign_key="b", title="Oferta B", company="Smiles", hc_score=42)

    ranking = build_global_ranking([lower, second, higher_duplicate])

    assert [item.campaign_key for item in ranking] == ["a", "b"]
    assert [item.hc_score for item in ranking] == [55, 42]


def test_post_global_scan_returns_consolidated_ranking(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app = FastAPI()
    app.include_router(router, prefix="/api")

    def override_get_db():
        with testing_session() as db:
            yield db

    campaigns = {
        "Livelo": _campaign(
            campaign_key="livelo",
            title="Livelo 50",
            company="Livelo",
            hc_score=50,
        ),
        "Esfera": _campaign(
            campaign_key="esfera",
            title="Esfera 70",
            company="Esfera",
            hc_score=70,
        ),
    }

    class FakeCollector:
        def __init__(self, source):
            self.source_name = source

        def run(self, db):
            items = [campaigns[self.source_name]] if self.source_name in campaigns else []
            return CollectorScanResult(
                source=self.source_name,
                analyzed=len(items),
                inserted=len(items),
                duplicates=0,
                campaigns=items,
            )

    names = {
        "livelo": "Livelo",
        "esfera": "Esfera",
        "smiles": "Smiles",
        "latam-pass": "LATAM Pass",
        "azul-fidelidade": "Azul Fidelidade",
    }
    monkeypatch.setattr(
        campaigns_api,
        "get_collector",
        lambda source: FakeCollector(names[source]),
    )
    app.dependency_overrides[get_db] = override_get_db

    response = TestClient(app).post("/api/scan/all")
    payload = response.json()

    assert response.status_code == 200
    assert payload["analyzed"] == 2
    assert len(payload["sources"]) == 5
    assert [item["campaign_key"] for item in payload["ranking"]] == ["esfera", "livelo"]
