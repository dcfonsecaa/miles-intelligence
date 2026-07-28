from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.campaigns import scan_all as scan_all_campaigns
from app.core.database import get_db
from app.schemas.campaign import GlobalScanResult, ScanCampaignRead

router = APIRouter(prefix="/scan", tags=["scanner"])


def build_global_ranking(campaigns: list[ScanCampaignRead]) -> list[ScanCampaignRead]:
    unique: dict[str, ScanCampaignRead] = {}
    for campaign in campaigns:
        current = unique.get(campaign.campaign_key)
        if current is None or campaign.hc_score > current.hc_score:
            unique[campaign.campaign_key] = campaign
    return sorted(
        unique.values(),
        key=lambda campaign: (-campaign.hc_score, campaign.company, campaign.title),
    )


@router.post("/all", response_model=GlobalScanResult)
def scan_all(db: Session = Depends(get_db)):
    result = scan_all_campaigns(db)
    return GlobalScanResult(
        **result.model_dump(),
        ranking=build_global_ranking(result.campaigns),
    )
