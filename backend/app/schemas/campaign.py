from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CostStatus(str, Enum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    ESTIMATED = "estimated"


class CampaignType(str, Enum):
    SUBSCRIPTION = "subscription"
    UPGRADE = "upgrade"
    POINTS_PURCHASE = "points_purchase"
    TRANSFER_BONUS = "transfer_bonus"
    CARD_ACQUISITION = "card_acquisition"
    ACCOUNT_OPENING = "account_opening"
    INSURANCE = "insurance"
    INVESTMENT = "investment"
    SHOPPING = "shopping"
    TRAVEL = "travel"
    OTHER = "other"


class Modality(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"
    ONE_TIME = "one_time"
    RECURRING = "recurring"
    UNKNOWN = "unknown"


class CampaignStatus(str, Enum):
    DETECTED = "detected"
    ACTIVE = "active"
    EXPIRED = "expired"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ExtractionConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CampaignCreate(BaseModel):
    company: str = Field(min_length=2, max_length=120)
    program_name: str | None = None
    campaign_type: CampaignType = CampaignType.OTHER
    modality: Modality = Modality.UNKNOWN
    partner_name: str | None = None
    title: str = Field(min_length=3, max_length=255)
    normalized_title: str = ""
    source_url: str
    regulation_url: str | None = None
    category: str = "outros"
    bonus_points: int = Field(default=0, ge=0)
    duration_months: int | None = Field(default=None, ge=1)
    monthly_points: int | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    cost_brl: float | None = Field(default=None, ge=0)
    cost_status: CostStatus = CostStatus.UNKNOWN
    eligibility: str | None = None
    status: CampaignStatus = CampaignStatus.DETECTED
    extraction_confidence: ExtractionConfidence = ExtractionConfidence.LOW
    extraction_notes: str = ""
    summary: str = ""
    campaign_key: str = ""
    raw_data: str = "{}"


class CampaignRead(CampaignCreate):
    id: int
    cpm: float | None
    hc_score: float
    anomaly_score: float
    detected_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScanCampaignRead(CampaignRead):
    action: str
    change_type: str
    analysis_status: str
    recommendation_level: str
    confidence_level: str
    attention_required: bool


class ScanResult(BaseModel):
    analyzed: int
    inserted: int
    updated: int = 0
    unchanged: int = 0
    errors: int = 0
    duplicates: int
    campaigns: list[ScanCampaignRead]


class CollectorScanResult(ScanResult):
    source: str


class CampaignRawRead(BaseModel):
    id: int
    campaign_key: str
    raw: dict[str, Any]
