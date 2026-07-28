from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.campaign_snapshot import CampaignSnapshot
from app.schemas.intelligence import ChangeType
from app.services.history_engine import create_snapshot


def migrate_history_engine(engine: Engine) -> None:
    with Session(engine) as db:
        campaigns = list(db.scalars(select(Campaign).order_by(Campaign.id)))
        changed = False
        for campaign in campaigns:
            existing = db.scalar(
                select(CampaignSnapshot.id)
                .where(CampaignSnapshot.campaign_id == campaign.id)
                .limit(1)
            )
            if existing is not None:
                continue
            create_snapshot(
                db,
                campaign,
                change_type=ChangeType.CREATED,
                change_summary="Snapshot inicial criado para campanha existente.",
            )
            changed = True
        if changed:
            db.commit()
