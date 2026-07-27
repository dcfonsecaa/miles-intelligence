from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CampaignCreate(BaseModel):
    company: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=3, max_length=255)
    source_url: str
    category: str = "outros"
    bonus_points: int = Field(default=0, ge=0)
    cost_brl: float = Field(default=0, ge=0)
    summary: str = ""


class CampaignRead(CampaignCreate):
    id: int
    cpm: float | None
    hc_score: float
    anomaly_score: float
    status: str
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScanResult(BaseModel):
    analyzed: int
    inserted: int
    duplicates: int
    campaigns: list[CampaignRead]
