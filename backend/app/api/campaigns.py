import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import (
    CollectorError,
    find_existing_campaign,
    persist_campaigns,
)
from app.collectors.registry import get_collector
from app.core.database import get_db
from app.models.campaign import Campaign
from app.schemas.campaign import (
    CampaignCreate,
    CollectorScanResult,
    CampaignRawRead,
    CampaignRead,
    ScanResult,
)
from app.schemas.intelligence import (
    CampaignIntelligenceRead,
    CampaignSnapshotRead,
    ChangeType,
    RecalculationResult,
)
from app.services.campaign_normalizer import normalize_campaign
from app.services.history_engine import create_snapshot, list_snapshots
from app.services.intelligence_engine import (
    analyze_campaign,
    recalculate_all,
)
from app.services.scanner import collect_demo_campaigns
from app.services.scoring import calculate_scores

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

# Fachada de compatibilidade para imports e testes anteriores.
_persist_campaigns = persist_campaigns


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


@router.get("/{campaign_id}/history", response_model=list[CampaignSnapshotRead])
def get_campaign_history(campaign_id: int, db: Session = Depends(get_db)):
    if db.get(Campaign, campaign_id) is None:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    return list_snapshots(db, campaign_id)


@router.get("/{campaign_id}/intelligence", response_model=CampaignIntelligenceRead)
def get_campaign_intelligence(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    intelligence = analyze_campaign(db, campaign)
    db.commit()
    return intelligence


@router.post("", response_model=CampaignRead, status_code=201)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    normalized = normalize_campaign(payload)
    if find_existing_campaign(db, normalized):
        raise HTTPException(status_code=409, detail="Campanha já cadastrada.")
    scores = calculate_scores(
        bonus_points=normalized.bonus_points,
        cost_brl=normalized.cost_brl,
        cost_status=normalized.cost_status.value,
    )
    campaign = Campaign(**normalized.model_dump(), **scores.__dict__)
    db.add(campaign)
    try:
        db.flush()
        create_snapshot(
            db,
            campaign,
            change_type=ChangeType.CREATED,
            change_summary="Campanha cadastrada manualmente.",
        )
        analyze_campaign(db, campaign)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(campaign)
    return campaign


@router.post("/scan-demo", response_model=ScanResult)
def scan_demo(db: Session = Depends(get_db)):
    return _persist_campaigns(collect_demo_campaigns(), db)


def _run_collector(source: str, db: Session) -> CollectorScanResult:
    try:
        return get_collector(source).run(db)
    except CollectorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/scan/livelo", response_model=CollectorScanResult)
def scan_livelo(db: Session = Depends(get_db)):
    return _run_collector("livelo", db)


@router.post("/scan/esfera", response_model=CollectorScanResult)
def scan_esfera(db: Session = Depends(get_db)):
    return _run_collector("esfera", db)


@router.post("/scan/smiles", response_model=CollectorScanResult)
def scan_smiles(db: Session = Depends(get_db)):
    return _run_collector("smiles", db)


@router.post("/recalculate-intelligence", response_model=RecalculationResult)
def recalculate_intelligence(db: Session = Depends(get_db)):
    analyses = recalculate_all(db)
    return RecalculationResult(recalculated=len(analyses), analyses=analyses)
