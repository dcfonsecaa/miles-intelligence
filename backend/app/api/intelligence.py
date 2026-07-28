from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.campaign import Campaign
from app.schemas.campaign import CampaignRead
from app.schemas.intelligence import (
    ChangeType,
    HighlightCampaign,
    IntelligenceHighlights,
)
from app.services.history_engine import list_snapshots
from app.services.intelligence_engine import analyze_campaign, get_stored_intelligence

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


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
