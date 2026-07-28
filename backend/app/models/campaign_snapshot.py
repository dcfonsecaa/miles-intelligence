from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CampaignSnapshot(Base):
    __tablename__ = "campaign_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    title: Mapped[str] = mapped_column(String(255))
    normalized_title: Mapped[str] = mapped_column(String(255))
    bonus_points: Mapped[int] = mapped_column(Integer, default=0)
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_brl: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_status: Mapped[str] = mapped_column(String(20), default="unknown")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    campaign_status: Mapped[str] = mapped_column(String(30), default="detected")
    regulation_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    change_type: Mapped[str] = mapped_column(String(30))
    change_summary: Mapped[str] = mapped_column(Text, default="")
    raw_data: Mapped[str] = mapped_column(Text, default="{}")
