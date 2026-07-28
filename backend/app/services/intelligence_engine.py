from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.campaign_intelligence import CampaignIntelligence
from app.models.campaign_snapshot import CampaignSnapshot
from app.schemas.intelligence import (
    AnalysisStatus,
    CampaignIntelligenceRead,
    IntelligenceConfidence,
    RecommendationLevel,
)
from app.services.history_engine import list_snapshots


def _snapshot_cpm(snapshot: CampaignSnapshot) -> float | None:
    if snapshot.cost_status != "known" or snapshot.cost_brl is None or snapshot.bonus_points <= 0:
        return None
    return round(snapshot.cost_brl / snapshot.bonus_points * 1000, 2)


def _peer_snapshots(db: Session, campaign: Campaign) -> list[CampaignSnapshot]:
    return list(
        db.scalars(
            select(CampaignSnapshot)
            .join(Campaign, Campaign.id == CampaignSnapshot.campaign_id)
            .where(
                Campaign.company == campaign.company,
                Campaign.campaign_type == campaign.campaign_type,
            )
            .order_by(CampaignSnapshot.captured_at, CampaignSnapshot.id)
        )
    )


def _as_read(model: CampaignIntelligence) -> CampaignIntelligenceRead:
    try:
        reasons = json.loads(model.reasons)
    except json.JSONDecodeError:
        reasons = [model.reasons]
    return CampaignIntelligenceRead(
        campaign_id=model.campaign_id,
        analysis_status=model.analysis_status,
        recommendation_level=model.recommendation_level,
        confidence_level=model.confidence_level,
        historical_position=model.historical_position,
        points_change_percent=model.points_change_percent,
        is_points_record=model.is_points_record,
        is_lowest_cpm_record=model.is_lowest_cpm_record,
        attention_required=model.attention_required,
        reasons=reasons,
        recommendation_text=model.recommendation_text,
        analyzed_at=model.analyzed_at,
    )


def analyze_campaign(db: Session, campaign: Campaign) -> CampaignIntelligenceRead:
    own_snapshots = list_snapshots(db, campaign.id)
    previous = own_snapshots[-2] if len(own_snapshots) >= 2 else None
    points_change_percent = None
    if previous and previous.bonus_points > 0:
        points_change_percent = round(
            (campaign.bonus_points - previous.bonus_points) / previous.bonus_points * 100,
            2,
        )

    current_snapshot_id = own_snapshots[-1].id if own_snapshots else None
    peers = _peer_snapshots(db, campaign)
    prior_peers = [snapshot for snapshot in peers if snapshot.id != current_snapshot_id]
    prior_points = [snapshot.bonus_points for snapshot in prior_peers if snapshot.bonus_points > 0]
    historical_average = mean(prior_points) if prior_points else None
    historical_max = max(prior_points) if prior_points else None
    is_points_record = historical_max is not None and campaign.bonus_points > historical_max

    if historical_average is None:
        historical_position = "insufficient_data"
    elif campaign.bonus_points > historical_average * 1.1:
        historical_position = "above_average"
    elif campaign.bonus_points < historical_average * 0.9:
        historical_position = "below_average"
    else:
        historical_position = "near_average"

    current_cpm = campaign.cpm if campaign.cost_status == "known" else None
    prior_cpms = [value for snapshot in prior_peers if (value := _snapshot_cpm(snapshot)) is not None]
    average_cpm = mean(prior_cpms) if prior_cpms else None
    is_lowest_cpm_record = (
        current_cpm is not None and bool(prior_cpms) and current_cpm < min(prior_cpms)
    )

    reasons: list[str] = []
    if is_points_record:
        reasons.append("Recorde de pontos para a mesma empresa e tipo de campanha.")
    if points_change_percent is not None:
        reasons.append(f"Variação de pontos de {points_change_percent:+.2f}% em relação ao snapshot anterior.")
    if historical_average is not None:
        reasons.append(f"Média histórica comparável: {historical_average:,.0f} pontos.".replace(",", "."))
    if is_lowest_cpm_record:
        reasons.append("Menor CPM conhecido no histórico comparável.")

    cost_changed = (
        previous is not None
        and (
            previous.cost_brl != campaign.cost_brl
            or previous.cost_status != campaign.cost_status
        )
    )
    ending_soon = (
        campaign.end_date is not None
        and date.today() <= campaign.end_date <= date.today() + timedelta(days=7)
    )
    if ending_soon:
        reasons.append("Prazo de encerramento em até sete dias.")
    if cost_changed:
        reasons.append("Mudança relevante de custo detectada.")

    analysis_status = (
        AnalysisStatus.COMPLETE
        if campaign.cost_status == "known" and campaign.cost_brl is not None and campaign.cpm is not None
        else AnalysisStatus.PRELIMINARY
    )
    attention_required = bool(
        is_points_record
        or (points_change_percent is not None and points_change_percent > 20)
        or (
            current_cpm is not None
            and average_cpm is not None
            and current_cpm < average_cpm * 0.8
        )
        or cost_changed
        or ending_soon
    )

    if analysis_status == AnalysisStatus.PRELIMINARY:
        recommendation_level = (
            RecommendationLevel.ANALYZE_NOW if attention_required else RecommendationLevel.MONITOR
        )
        confidence_level = (
            IntelligenceConfidence.MEDIUM if len(prior_points) >= 2 else IntelligenceConfidence.LOW
        )
        reasons.append("Custo ainda não confirmado; CPM e avaliação financeira permanecem preliminares.")
        recommendation_text = (
            "Confirme o custo, a elegibilidade e as regras do regulamento antes de qualquer decisão financeira."
        )
    else:
        confidence_level = (
            IntelligenceConfidence.HIGH
            if len(prior_cpms) >= 3
            else IntelligenceConfidence.MEDIUM
            if prior_cpms
            else IntelligenceConfidence.LOW
        )
        if is_lowest_cpm_record and is_points_record:
            recommendation_level = RecommendationLevel.ATTRACTIVE
        elif is_lowest_cpm_record or (
            current_cpm is not None
            and average_cpm is not None
            and current_cpm < average_cpm * 0.9
        ):
            recommendation_level = RecommendationLevel.POTENTIALLY_ATTRACTIVE
        elif (
            current_cpm is not None
            and average_cpm is not None
            and current_cpm > average_cpm * 1.2
        ):
            recommendation_level = RecommendationLevel.UNATTRACTIVE
        elif not prior_cpms:
            recommendation_level = RecommendationLevel.INSUFFICIENT_DATA
        else:
            recommendation_level = (
                RecommendationLevel.ANALYZE_NOW
                if attention_required
                else RecommendationLevel.MONITOR
            )
        recommendation_text = (
            "Compare o CPM, o prazo e as regras com alternativas antes da decisão."
            if recommendation_level != RecommendationLevel.INSUFFICIENT_DATA
            else "Ainda não há histórico financeiro conhecido suficiente para recomendar esta campanha."
        )

    model = db.scalar(
        select(CampaignIntelligence).where(CampaignIntelligence.campaign_id == campaign.id)
    )
    if model is None:
        model = CampaignIntelligence(campaign_id=campaign.id)
        db.add(model)
    model.analysis_status = analysis_status.value
    model.recommendation_level = recommendation_level.value
    model.confidence_level = confidence_level.value
    model.historical_position = historical_position
    model.points_change_percent = points_change_percent
    model.is_points_record = is_points_record
    model.is_lowest_cpm_record = is_lowest_cpm_record
    model.attention_required = attention_required
    model.reasons = json.dumps(reasons, ensure_ascii=False)
    model.recommendation_text = recommendation_text
    model.analyzed_at = datetime.now(UTC).replace(tzinfo=None)
    db.flush()
    return _as_read(model)


def recalculate_all(db: Session) -> list[CampaignIntelligenceRead]:
    analyses = [
        analyze_campaign(db, campaign)
        for campaign in db.scalars(select(Campaign).order_by(Campaign.id))
    ]
    db.commit()
    return analyses


def get_stored_intelligence(
    db: Session, campaign_id: int
) -> CampaignIntelligenceRead | None:
    model = db.scalar(
        select(CampaignIntelligence).where(CampaignIntelligence.campaign_id == campaign_id)
    )
    return _as_read(model) if model else None
