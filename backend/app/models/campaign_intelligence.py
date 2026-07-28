from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CampaignIntelligence(Base):
    __tablename__ = "campaign_intelligence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), unique=True, index=True
    )
    analysis_status: Mapped[str] = mapped_column(String(20))
    recommendation_level: Mapped[str] = mapped_column(String(40))
    confidence_level: Mapped[str] = mapped_column(String(20))
    historical_position: Mapped[str] = mapped_column(String(40))
    points_change_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_points_record: Mapped[bool] = mapped_column(Boolean, default=False)
    is_lowest_cpm_record: Mapped[bool] = mapped_column(Boolean, default=False)
    attention_required: Mapped[bool] = mapped_column(Boolean, default=False)
    reasons: Mapped[str] = mapped_column(Text, default="[]")
    recommendation_text: Mapped[str] = mapped_column(Text)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
