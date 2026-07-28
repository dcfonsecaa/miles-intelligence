from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.campaign import Campaign
from app.models.campaign_snapshot import CampaignSnapshot
from app.schemas.campaign import CampaignRead
from app.schemas.intelligence import (
    ChangeType,
    HighlightCampaign,
    IntelligenceHighlights,
    IntelligenceDashboard,
    CampaignAIAnalysis,
    RecentHistoryItem,
)
from app.services.history_engine import list_snapshots
from app.services.intelligence_engine import analyze_campaign, get_stored_intelligence
from app.services.ai_intelligence_engine import campaign_insight_engine

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


def _highlight(db: Session, campaign: Campaign) -> HighlightCampaign:
    intelligence = get_stored_intelligence(db, campaign.id) or analyze_campaign(db, campaign)
    snapshots = list_snapshots(db, campaign.id)
    latest_change = ChangeType(snapshots[-1].change_type) if snapshots else ChangeType.CREATED
    return HighlightCampaign(
        campaign=CampaignRead.model_validate(campaign),
        intelligence=intelligence,
        latest_change_type=latest_change,
    )


@router.get("/highlights", response_model=IntelligenceHighlights)
def get_highlights(db: Session = Depends(get_db)):
    groups = {
        "new_campaigns": [],
        "changed_campaigns": [],
        "points_records": [],
        "attention_required": [],
        "unknown_cost": [],
        "preliminary_analyses": [],
    }
    for campaign in db.scalars(select(Campaign).order_by(Campaign.detected_at.desc())):
        intelligence = get_stored_intelligence(db, campaign.id) or analyze_campaign(db, campaign)
        snapshots = list_snapshots(db, campaign.id)
        latest_change = (
            ChangeType(snapshots[-1].change_type) if snapshots else ChangeType.CREATED
        )
        item = HighlightCampaign(
            campaign=CampaignRead.model_validate(campaign),
            intelligence=intelligence,
            latest_change_type=latest_change,
        )
        if latest_change == ChangeType.CREATED:
            groups["new_campaigns"].append(item)
        elif latest_change != ChangeType.UNCHANGED:
            groups["changed_campaigns"].append(item)
        if intelligence.is_points_record:
            groups["points_records"].append(item)
        if intelligence.attention_required:
            groups["attention_required"].append(item)
        if campaign.cost_status == "unknown":
            groups["unknown_cost"].append(item)
        if intelligence.analysis_status.value == "preliminary":
            groups["preliminary_analyses"].append(item)
    db.commit()
    return IntelligenceHighlights(**groups)


@router.get("/dashboard", response_model=IntelligenceDashboard)
def get_dashboard(
    program: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    campaigns = list(db.scalars(select(Campaign).order_by(Campaign.hc_score.desc())))
    programs = sorted(
        {
            campaign.program_name or campaign.company
            for campaign in campaigns
            if campaign.program_name or campaign.company
        }
    )
    if program:
        campaigns = [
            campaign
            for campaign in campaigns
            if (campaign.program_name or campaign.company) == program
        ]

    ranking = [_highlight(db, campaign) for campaign in campaigns[:10]]
    today = datetime.now(UTC).date()
    best_today = next(
        (
            item
            for item in ranking
            if item.campaign.detected_at.replace(tzinfo=UTC).date() == today
        ),
        None,
    )

    campaign_by_id = {campaign.id: campaign for campaign in campaigns}
    snapshots = list(
        db.scalars(
            select(CampaignSnapshot)
            .where(CampaignSnapshot.campaign_id.in_(campaign_by_id))
            .order_by(CampaignSnapshot.captured_at.desc())
            .limit(10)
        )
    ) if campaign_by_id else []
    recent_history = [
        RecentHistoryItem(
            snapshot_id=snapshot.id,
            campaign_id=snapshot.campaign_id,
            company=campaign_by_id[snapshot.campaign_id].company,
            program_name=campaign_by_id[snapshot.campaign_id].program_name,
            title=snapshot.title,
            captured_at=snapshot.captured_at,
            change_type=ChangeType(snapshot.change_type),
            change_summary=snapshot.change_summary,
            hc_score=campaign_by_id[snapshot.campaign_id].hc_score,
        )
        for snapshot in snapshots
    ]
    last_updated = max((campaign.updated_at for campaign in campaigns), default=None)
    db.commit()
    return IntelligenceDashboard(
        best_campaign_today=best_today,
        ranking=ranking,
        recent_history=recent_history,
        last_updated_at=last_updated,
        programs=programs,
    )


@router.get("/{campaign_id}/ai-analysis", response_model=CampaignAIAnalysis)
def get_ai_analysis(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    analysis = campaign_insight_engine.analyze(db, campaign)
    db.commit()
    return analysis
