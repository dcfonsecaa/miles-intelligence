import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.campaign import Campaign
from app.schemas.campaign import (
    CampaignCreate,
    CampaignRawRead,
    CampaignRead,
    ScanCampaignRead,
    ScanResult,
)
from app.services.campaign_normalizer import normalize_campaign
from app.services.livelo_collector import collect_livelo_campaigns
from app.services.scanner import collect_demo_campaigns
from app.services.scoring import calculate_scores

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _persist_campaigns(detected: list[CampaignCreate], db: Session) -> ScanResult:
    inserted_campaigns: list[Campaign] = []
    returned_campaigns: list[ScanCampaignRead] = []
    duplicates = 0

    for payload in detected:
        normalized = normalize_campaign(payload)
        existing = db.scalar(select(Campaign).where(Campaign.campaign_key == normalized.campaign_key))
        if existing:
            duplicates += 1
            returned_campaigns.append(
                ScanCampaignRead(
                    **CampaignRead.model_validate(existing).model_dump(),
                    action="duplicate",
                )
            )
            continue

        scores = calculate_scores(
            bonus_points=normalized.bonus_points,
            cost_brl=normalized.cost_brl,
            cost_status=normalized.cost_status.value,
        )
        campaign = Campaign(**normalized.model_dump(), **scores.__dict__)
        db.add(campaign)
        try:
            db.flush()
        except Exception:
            db.rollback()
            raise
        inserted_campaigns.append(campaign)
        returned_campaigns.append(
            ScanCampaignRead(
                **CampaignRead.model_validate(campaign).model_dump(),
                action="inserted",
            )
        )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return ScanResult(
        analyzed=len(detected),
        inserted=len(inserted_campaigns),
        duplicates=duplicates,
        campaigns=returned_campaigns,
    )


@router.get("", response_model=list[CampaignRead])
def list_campaigns(db: Session = Depends(get_db)):
    return db.scalars(select(Campaign).order_by(Campaign.hc_score.desc())).all()


@router.get("/{campaign_id}", response_model=CampaignRead)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    return campaign


@router.get("/{campaign_id}/raw", response_model=CampaignRawRead)
def get_campaign_raw(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    try:
        raw = json.loads(campaign.raw_data or "{}")
    except json.JSONDecodeError:
        raw = {"legacy_raw_data": campaign.raw_data}
    return CampaignRawRead(id=campaign.id, campaign_key=campaign.campaign_key, raw=raw)


@router.post("", response_model=CampaignRead, status_code=201)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    normalized = normalize_campaign(payload)
    existing = db.scalar(select(Campaign).where(Campaign.campaign_key == normalized.campaign_key))
    if existing:
        raise HTTPException(status_code=409, detail="Campanha já cadastrada.")
    scores = calculate_scores(
        bonus_points=normalized.bonus_points,
        cost_brl=normalized.cost_brl,
        cost_status=normalized.cost_status.value,
    )
    campaign = Campaign(**normalized.model_dump(), **scores.__dict__)
    db.add(campaign)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(campaign)
    return campaign


@router.post("/scan-demo", response_model=ScanResult)
def scan_demo(db: Session = Depends(get_db)):
    return _persist_campaigns(collect_demo_campaigns(), db)


@router.post("/scan/livelo", response_model=ScanResult)
def scan_livelo(db: Session = Depends(get_db)):
    try:
        result = collect_livelo_campaigns()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao consultar a Livelo: {exc}") from exc
    return _persist_campaigns(result.campaigns, db)
