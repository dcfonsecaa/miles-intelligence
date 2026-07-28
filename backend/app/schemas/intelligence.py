from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.schemas.campaign import CampaignRead


class ChangeType(str, Enum):
    CREATED = "created"
    UNCHANGED = "unchanged"
    POINTS_INCREASED = "points_increased"
    POINTS_DECREASED = "points_decreased"
    COST_CHANGED = "cost_changed"
    DURATION_CHANGED = "duration_changed"
    DATES_CHANGED = "dates_changed"
    STATUS_CHANGED = "status_changed"
    TITLE_CHANGED = "title_changed"
    MULTIPLE_CHANGES = "multiple_changes"


class AnalysisStatus(str, Enum):
    PRELIMINARY = "preliminary"
    COMPLETE = "complete"


class RecommendationLevel(str, Enum):
    INSUFFICIENT_DATA = "insufficient_data"
    MONITOR = "monitor"
    ANALYZE_NOW = "analyze_now"
    POTENTIALLY_ATTRACTIVE = "potentially_attractive"
    ATTRACTIVE = "attractive"
    UNATTRACTIVE = "unattractive"


class IntelligenceConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CampaignSnapshotRead(BaseModel):
    id: int
    campaign_id: int
    captured_at: datetime
    title: str
    normalized_title: str
    bonus_points: int
    duration_months: int | None
    monthly_points: int | None
    cost_brl: float | None
    cost_status: str
    start_date: date | None = None
    end_date: date | None = None
    campaign_status: str
    regulation_url: str | None
    content_hash: str
    change_type: ChangeType
    change_summary: str
    raw_data: str

    model_config = ConfigDict(from_attributes=True)


class CampaignIntelligenceRead(BaseModel):
    campaign_id: int
    analysis_status: AnalysisStatus
    recommendation_level: RecommendationLevel
    confidence_level: IntelligenceConfidence
    historical_position: str
    points_change_percent: float | None
    is_points_record: bool
    is_lowest_cpm_record: bool
    attention_required: bool
    reasons: list[str]
    recommendation_text: str
    analyzed_at: datetime


class HighlightCampaign(BaseModel):
    campaign: CampaignRead
    intelligence: CampaignIntelligenceRead
    latest_change_type: ChangeType


class IntelligenceHighlights(BaseModel):
    new_campaigns: list[HighlightCampaign]
    changed_campaigns: list[HighlightCampaign]
    points_records: list[HighlightCampaign]
    attention_required: list[HighlightCampaign]
    unknown_cost: list[HighlightCampaign]
    preliminary_analyses: list[HighlightCampaign]


class RecalculationResult(BaseModel):
    recalculated: int
    analyses: list[CampaignIntelligenceRead]
