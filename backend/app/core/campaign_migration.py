from __future__ import annotations

from datetime import datetime

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.models.campaign import Campaign
from app.schemas.campaign import CampaignCreate, CostStatus
from app.services.campaign_normalizer import normalize_campaign
from app.services.scoring import calculate_scores

TARGET_COLUMNS = {column.name for column in Campaign.__table__.columns}


def _legacy_datetime(value, fallback: datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return fallback


def _requires_rebuild(connection) -> bool:
    inspector = inspect(connection)
    columns = {column["name"] for column in inspector.get_columns("campaigns")}
    unique_constraints = inspector.get_unique_constraints("campaigns")
    source_is_unique = any(
        constraint.get("column_names") == ["source_url"] for constraint in unique_constraints
    )
    return not TARGET_COLUMNS.issubset(columns) or source_is_unique


def migrate_campaign_model_v2(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as connection:
        inspector = inspect(connection)
        if "campaigns" not in inspector.get_table_names():
            return
        if not _requires_rebuild(connection):
            connection.execute(
                text(
                    """
                    UPDATE campaigns
                    SET cost_brl = NULL, cost_status = 'unknown', cpm = NULL
                    WHERE lower(company) = 'livelo' AND cost_brl = 0
                    """
                )
            )
            return

        legacy_rows = connection.execute(text("SELECT * FROM campaigns")).mappings().all()
        for index in inspector.get_indexes("campaigns"):
            connection.execute(text(f'DROP INDEX IF EXISTS "{index["name"]}"'))
        connection.execute(text("ALTER TABLE campaigns RENAME TO campaigns_legacy_v1"))
        Campaign.__table__.create(bind=connection)

        now = datetime.utcnow()
        for row in legacy_rows:
            company = row.get("company") or "Unknown"
            legacy_cost = row.get("cost_brl")
            cost_status = (
                CostStatus.UNKNOWN
                if company.casefold() == "livelo" and legacy_cost == 0
                else CostStatus.KNOWN
                if legacy_cost is not None
                else CostStatus.UNKNOWN
            )
            normalized = normalize_campaign(
                CampaignCreate(
                    company=company,
                    title=row.get("title") or "Legacy campaign",
                    source_url=row.get("source_url") or f"legacy://campaign/{row['id']}",
                    category=row.get("category") or "outros",
                    bonus_points=row.get("bonus_points") or 0,
                    cost_brl=legacy_cost,
                    cost_status=cost_status,
                    summary=row.get("summary") or "",
                    status=row.get("status") or "detected",
                )
            )
            scores = calculate_scores(
                bonus_points=normalized.bonus_points,
                cost_brl=normalized.cost_brl,
                cost_status=normalized.cost_status.value,
            )
            values = normalized.model_dump()
            values.update(
                {
                    "id": row["id"],
                    "cpm": scores.cpm,
                    "hc_score": scores.hc_score,
                    "anomaly_score": scores.anomaly_score,
                    "detected_at": _legacy_datetime(row.get("detected_at"), now),
                    "updated_at": now,
                }
            )
            connection.execute(Campaign.__table__.insert().values(**values))

        connection.execute(text("DROP TABLE campaigns_legacy_v1"))
