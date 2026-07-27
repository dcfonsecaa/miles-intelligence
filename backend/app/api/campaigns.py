from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.campaign import Campaign
from app.schemas.campaign import CampaignCreate, CampaignRead, ScanResult
from app.services.scanner import collect_demo_campaigns
from app.services.scoring import calculate_scores

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignRead])
def list_campaigns(db: Session = Depends(get_db)):
    return db.scalars(select(Campaign).order_by(Campaign.hc_score.desc())).all()


@router.post("", response_model=CampaignRead, status_code=201)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    scores = calculate_scores(bonus_points=payload.bonus_points, cost_brl=payload.cost_brl)
    campaign = Campaign(**payload.model_dump(), **scores.__dict__)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/scan-demo", response_model=ScanResult)
def scan_demo(db: Session = Depends(get_db)):
    detected = collect_demo_campaigns()
    inserted: list[Campaign] = []
    duplicates = 0

    for payload in detected:
        existing = db.scalar(select(Campaign).where(Campaign.source_url == payload.source_url))
        if existing:
            duplicates += 1
            inserted.append(existing)
            continue

        scores = calculate_scores(bonus_points=payload.bonus_points, cost_brl=payload.cost_brl)
        campaign = Campaign(**payload.model_dump(), **scores.__dict__)
        db.add(campaign)
        inserted.append(campaign)

    db.commit()
    for campaign in inserted:
        db.refresh(campaign)

    return ScanResult(
        analyzed=len(detected),
        inserted=len(detected) - duplicates,
        duplicates=duplicates,
        campaigns=inserted,
    )
