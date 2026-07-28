from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.campaign_snapshot import CampaignSnapshot
from app.schemas.campaign import CampaignCreate
from app.schemas.intelligence import ChangeType


@dataclass(frozen=True)
class ChangeDetection:
    change_type: ChangeType
    summary: str
    changed_fields: tuple[str, ...]


def _state_payload(source: Campaign | CampaignCreate) -> dict:
    status = getattr(source, "status", "detected")
    status = getattr(status, "value", status)
    cost_status = getattr(source, "cost_status", "unknown")
    cost_status = getattr(cost_status, "value", cost_status)
    return {
        "title": source.title,
        "normalized_title": source.normalized_title,
        "bonus_points": source.bonus_points,
        "duration_months": source.duration_months,
        "monthly_points": source.monthly_points,
        "cost_brl": source.cost_brl,
        "cost_status": cost_status,
        "start_date": source.start_date.isoformat() if source.start_date else None,
        "end_date": source.end_date.isoformat() if source.end_date else None,
        "campaign_status": status,
        "regulation_url": source.regulation_url,
        "raw_data": source.raw_data,
    }


def content_hash(source: Campaign | CampaignCreate) -> str:
    payload = _state_payload(source)
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _format_brl(value: float | None, status: str) -> str:
    if status == "unknown" or value is None:
        return "desconhecido"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def detect_changes(current: Campaign, incoming: CampaignCreate) -> ChangeDetection:
    if content_hash(current) == content_hash(incoming):
        return ChangeDetection(ChangeType.UNCHANGED, "Nenhuma mudança relevante.", ())

    changes: list[tuple[str, ChangeType, str]] = []
    if current.bonus_points != incoming.bonus_points:
        direction = (
            ChangeType.POINTS_INCREASED
            if incoming.bonus_points > current.bonus_points
            else ChangeType.POINTS_DECREASED
        )
        verb = "aumentou" if direction == ChangeType.POINTS_INCREASED else "diminuiu"
        changes.append(
            (
                "bonus_points",
                direction,
                f"Pontuação {verb} de {current.bonus_points:,} para {incoming.bonus_points:,} pontos.".replace(
                    ",", "."
                ),
            )
        )
    current_cost_status = str(current.cost_status)
    incoming_cost_status = incoming.cost_status.value
    if current.cost_brl != incoming.cost_brl or current_cost_status != incoming_cost_status:
        changes.append(
            (
                "cost",
                ChangeType.COST_CHANGED,
                "Custo passou de "
                f"{_format_brl(current.cost_brl, current_cost_status)} para "
                f"{_format_brl(incoming.cost_brl, incoming_cost_status)}.",
            )
        )
    if current.duration_months != incoming.duration_months:
        changes.append(
            (
                "duration_months",
                ChangeType.DURATION_CHANGED,
                f"Duração passou de {current.duration_months or 'desconhecida'} para "
                f"{incoming.duration_months or 'desconhecida'} meses.",
            )
        )
    if current.start_date != incoming.start_date or current.end_date != incoming.end_date:
        changes.append(("dates", ChangeType.DATES_CHANGED, "O período da campanha foi alterado."))
    incoming_status = incoming.status.value
    if current.status != incoming_status:
        changes.append(
            (
                "status",
                ChangeType.STATUS_CHANGED,
                f"Status passou de {current.status} para {incoming_status}.",
            )
        )
    if current.title != incoming.title or current.normalized_title != incoming.normalized_title:
        changes.append(("title", ChangeType.TITLE_CHANGED, "O título da campanha foi alterado."))

    if not changes:
        return ChangeDetection(ChangeType.UNCHANGED, "Nenhuma mudança relevante.", ())
    change_type = changes[0][1] if len(changes) == 1 else ChangeType.MULTIPLE_CHANGES
    return ChangeDetection(
        change_type,
        " ".join(item[2] for item in changes),
        tuple(item[0] for item in changes),
    )


def create_snapshot(
    db: Session,
    campaign: Campaign,
    *,
    change_type: ChangeType,
    change_summary: str,
) -> CampaignSnapshot:
    snapshot = CampaignSnapshot(
        campaign_id=campaign.id,
        title=campaign.title,
        normalized_title=campaign.normalized_title,
        bonus_points=campaign.bonus_points,
        duration_months=campaign.duration_months,
        monthly_points=campaign.monthly_points,
        cost_brl=campaign.cost_brl,
        cost_status=campaign.cost_status,
        start_date=campaign.start_date,
        end_date=campaign.end_date,
        campaign_status=campaign.status,
        regulation_url=campaign.regulation_url,
        content_hash=content_hash(campaign),
        change_type=change_type.value,
        change_summary=change_summary,
        raw_data=campaign.raw_data,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def list_snapshots(db: Session, campaign_id: int) -> list[CampaignSnapshot]:
    return list(
        db.scalars(
            select(CampaignSnapshot)
            .where(CampaignSnapshot.campaign_id == campaign_id)
            .order_by(CampaignSnapshot.captured_at, CampaignSnapshot.id)
        )
    )
