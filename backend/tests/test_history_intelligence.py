from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.campaigns import _persist_campaigns, router as campaigns_router
from app.api.intelligence import router as intelligence_router
from app.core.database import Base, get_db
from app.core.history_migration import migrate_history_engine
from app.models.campaign import Campaign
from app.models.campaign_snapshot import CampaignSnapshot
from app.schemas.campaign import (
    CampaignCreate,
    CampaignType,
    CostStatus,
    Modality,
)
from app.services.intelligence_engine import analyze_campaign


def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _payload(
    *,
    points=74_000,
    duration=12,
    cost=None,
    cost_status=CostStatus.UNKNOWN,
    title="Campanha Clube Top",
):
    return CampaignCreate(
        company="Livelo",
        program_name="Clube Livelo",
        campaign_type=CampaignType.UPGRADE,
        modality=Modality.ANNUAL,
        title=title,
        source_url="https://www.livelo.com.br/regulamentos-ativos",
        regulation_url="https://assets.example.com/top.pdf",
        bonus_points=points,
        duration_months=duration,
        cost_brl=cost,
        cost_status=cost_status,
    )


def _latest_snapshot(db: Session) -> CampaignSnapshot:
    return db.scalar(select(CampaignSnapshot).order_by(CampaignSnapshot.id.desc()))


def test_new_campaign_creates_snapshot_and_identical_scan_is_not_redundant():
    engine = _engine()
    with Session(engine) as db:
        first = _persist_campaigns([_payload()], db)
        campaign_count = db.scalar(select(func.count()).select_from(Campaign))
        snapshot_count = db.scalar(select(func.count()).select_from(CampaignSnapshot))

        second = _persist_campaigns([_payload()], db)
        final_campaign_count = db.scalar(select(func.count()).select_from(Campaign))
        final_snapshot_count = db.scalar(select(func.count()).select_from(CampaignSnapshot))

    assert first.inserted == 1
    assert first.campaigns[0].action == "inserted"
    assert first.campaigns[0].change_type == "created"
    assert campaign_count == final_campaign_count == 1
    assert snapshot_count == final_snapshot_count == 1
    assert second.unchanged == 1
    assert second.campaigns[0].action == "unchanged"


def test_points_increase_and_decrease_are_detected():
    engine = _engine()
    with Session(engine) as db:
        _persist_campaigns([_payload(points=74_000)], db)
        increased = _persist_campaigns([_payload(points=96_000)], db)
        increase_snapshot = _latest_snapshot(db)
        decreased = _persist_campaigns([_payload(points=78_000)], db)
        decrease_snapshot = _latest_snapshot(db)

    assert increased.updated == 1
    assert increase_snapshot.change_type == "points_increased"
    assert "74.000 para 96.000" in increase_snapshot.change_summary
    assert decreased.updated == 1
    assert decrease_snapshot.change_type == "points_decreased"


def test_cost_duration_and_multiple_changes_are_detected():
    engine = _engine()
    with Session(engine) as db:
        _persist_campaigns([_payload()], db)
        _persist_campaigns(
            [_payload(cost=1_200, cost_status=CostStatus.KNOWN)],
            db,
        )
        cost_snapshot = _latest_snapshot(db)
        _persist_campaigns(
            [_payload(duration=18, cost=1_200, cost_status=CostStatus.KNOWN)],
            db,
        )
        duration_snapshot = _latest_snapshot(db)
        _persist_campaigns(
            [_payload(points=96_000, duration=12, cost=1_200, cost_status=CostStatus.KNOWN)],
            db,
        )
        multiple_snapshot = _latest_snapshot(db)

    assert cost_snapshot.change_type == "cost_changed"
    assert "R$ 1.200,00" in cost_snapshot.change_summary
    assert duration_snapshot.change_type == "duration_changed"
    assert multiple_snapshot.change_type == "multiple_changes"


def test_unknown_cost_is_preliminary_and_never_zero_cpm():
    engine = _engine()
    with Session(engine) as db:
        result = _persist_campaigns([_payload()], db)
        campaign = db.scalar(select(Campaign))
        intelligence = analyze_campaign(db, campaign)

    assert campaign.cost_brl is None
    assert campaign.cpm is None
    assert intelligence.analysis_status.value == "preliminary"
    assert intelligence.confidence_level.value != "high"
    assert "Confirme o custo" in intelligence.recommendation_text
    assert result.campaigns[0].analysis_status == "preliminary"


def test_points_record_and_change_percent_are_calculated():
    engine = _engine()
    with Session(engine) as db:
        _persist_campaigns([_payload(points=74_000)], db)
        _persist_campaigns([_payload(points=96_000)], db)
        campaign = db.scalar(select(Campaign))
        intelligence = analyze_campaign(db, campaign)

    assert intelligence.is_points_record is True
    assert intelligence.points_change_percent == 29.73
    assert intelligence.attention_required is True


def _client():
    engine = _engine()
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app = FastAPI()
    app.include_router(campaigns_router, prefix="/api")
    app.include_router(intelligence_router, prefix="/api")

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_history_intelligence_highlights_and_recalculation_endpoints():
    client = _client()
    created = client.post(
        "/api/campaigns",
        json={
            "company": "Livelo",
            "title": "Campanha Clube Top",
            "source_url": "https://assets.example.com/top.pdf",
            "bonus_points": 74000,
            "campaign_type": "upgrade",
            "modality": "annual",
        },
    )
    assert created.status_code == 201
    campaign_id = created.json()["id"]

    history = client.get(f"/api/campaigns/{campaign_id}/history")
    intelligence = client.get(f"/api/campaigns/{campaign_id}/intelligence")
    highlights = client.get("/api/intelligence/highlights")
    recalculation = client.post("/api/campaigns/recalculate-intelligence")

    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["change_type"] == "created"
    assert intelligence.status_code == 200
    assert intelligence.json()["analysis_status"] == "preliminary"
    assert highlights.status_code == 200
    assert len(highlights.json()["new_campaigns"]) == 1
    assert len(highlights.json()["unknown_cost"]) == 1
    assert len(highlights.json()["preliminary_analyses"]) == 1
    assert recalculation.status_code == 200
    assert recalculation.json()["recalculated"] == 1


def test_history_migration_preserves_existing_campaign_and_is_idempotent():
    engine = _engine()
    with Session(engine) as db:
        normalized = _payload().model_copy(
            update={
                "campaign_key": "a" * 64,
                "normalized_title": "Campanha Clube Top",
                "raw_data": "{}",
            }
        )
        campaign = Campaign(
            **normalized.model_dump(),
            cpm=None,
            hc_score=22.2,
            anomaly_score=18.5,
        )
        db.add(campaign)
        db.commit()
        original_id = campaign.id

    migrate_history_engine(engine)
    migrate_history_engine(engine)

    with Session(engine) as db:
        campaigns = list(db.scalars(select(Campaign)))
        snapshots = list(db.scalars(select(CampaignSnapshot)))
    assert len(campaigns) == 1
    assert campaigns[0].id == original_id
    assert len(snapshots) == 1
    assert snapshots[0].change_type == "created"
