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
from app.schemas.intelligence import (
    CampaignIntelligenceRead,
    CampaignSnapshotRead,
    ChangeType,
    RecalculationResult,
)
from app.services.campaign_normalizer import normalize_campaign
from app.services.history_engine import create_snapshot, detect_changes, list_snapshots
from app.services.intelligence_engine import (
    analyze_campaign,
    get_stored_intelligence,
    recalculate_all,
)
from app.services.livelo_collector import collect_livelo_campaigns
from app.services.scanner import collect_demo_campaigns
from app.services.scoring import calculate_scores

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _find_existing(db: Session, normalized: CampaignCreate) -> Campaign | None:
    exact = db.scalar(select(Campaign).where(Campaign.campaign_key == normalized.campaign_key))
    if exact is not None:
        return exact
    if not normalized.regulation_url:
        return None
    candidates = list(
        db.scalars(
            select(Campaign).where(
                Campaign.company == normalized.company,
                Campaign.regulation_url == normalized.regulation_url,
                Campaign.campaign_type == normalized.campaign_type.value,
                Campaign.modality == normalized.modality.value,
            )
        )
    )
    return candidates[0] if len(candidates) == 1 else None


def _apply_normalized_state(campaign: Campaign, normalized: CampaignCreate) -> None:
    for field, value in normalized.model_dump().items():
        setattr(campaign, field, value)
    scores = calculate_scores(
        bonus_points=normalized.bonus_points,
        cost_brl=normalized.cost_brl,
        cost_status=normalized.cost_status.value,
    )
    campaign.cpm = scores.cpm
    campaign.hc_score = scores.hc_score
    campaign.anomaly_score = scores.anomaly_score


def _scan_read(
    campaign: Campaign,
    *,
    action: str,
    change_type: str,
    intelligence: CampaignIntelligenceRead,
) -> ScanCampaignRead:
    return ScanCampaignRead(
        **CampaignRead.model_validate(campaign).model_dump(),
        action=action,
        change_type=change_type,
        analysis_status=intelligence.analysis_status.value,
        recommendation_level=intelligence.recommendation_level.value,
        confidence_level=intelligence.confidence_level.value,
        attention_required=intelligence.attention_required,
    )


def _persist_campaigns(detected: list[CampaignCreate], db: Session) -> ScanResult:
    returned: list[ScanCampaignRead] = []
    inserted = updated = unchanged = errors = 0

    for payload in detected:
        try:
            with db.begin_nested():
                normalized = normalize_campaign(payload)
                existing = _find_existing(db, normalized)
                if existing is None:
                    scores = calculate_scores(
                        bonus_points=normalized.bonus_points,
                        cost_brl=normalized.cost_brl,
                        cost_status=normalized.cost_status.value,
                    )
                    campaign = Campaign(**normalized.model_dump(), **scores.__dict__)
                    db.add(campaign)
                    db.flush()
                    snapshot = create_snapshot(
                        db,
                        campaign,
                        change_type=ChangeType.CREATED,
                        change_summary="Campanha detectada pela primeira vez.",
                    )
                    intelligence = analyze_campaign(db, campaign)
                    returned.append(
                        _scan_read(
                            campaign,
                            action="inserted",
                            change_type=snapshot.change_type,
                            intelligence=intelligence,
                        )
                    )
                    inserted += 1
                    continue

                change = detect_changes(existing, normalized)
                if change.change_type == ChangeType.UNCHANGED:
                    intelligence = get_stored_intelligence(db, existing.id) or analyze_campaign(
                        db, existing
                    )
                    returned.append(
                        _scan_read(
                            existing,
                            action="unchanged",
                            change_type=ChangeType.UNCHANGED.value,
                            intelligence=intelligence,
                        )
                    )
                    unchanged += 1
                    continue

                _apply_normalized_state(existing, normalized)
                db.flush()
                snapshot = create_snapshot(
                    db,
                    existing,
                    change_type=change.change_type,
                    change_summary=change.summary,
                )
                intelligence = analyze_campaign(db, existing)
                returned.append(
                    _scan_read(
                        existing,
                        action="updated",
                        change_type=snapshot.change_type,
                        intelligence=intelligence,
                    )
                )
                updated += 1
        except Exception:
            errors += 1

    db.commit()
    return ScanResult(
        analyzed=len(detected),
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
        errors=errors,
        duplicates=unchanged,
        campaigns=returned,
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
    if _find_existing(db, normalized):
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


@router.post("/scan/livelo", response_model=ScanResult)
def scan_livelo(db: Session = Depends(get_db)):
    try:
        result = collect_livelo_campaigns()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao consultar a Livelo: {exc}") from exc
    return _persist_campaigns(result.campaigns, db)


@router.post("/recalculate-intelligence", response_model=RecalculationResult)
def recalculate_intelligence(db: Session = Depends(get_db)):
    analyses = recalculate_all(db)
    return RecalculationResult(recalculated=len(analyses), analyses=analyses)
