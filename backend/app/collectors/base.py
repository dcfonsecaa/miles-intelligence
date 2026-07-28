from __future__ import annotations

from abc import ABC, abstractmethod

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.schemas.campaign import (
    CampaignCreate,
    CampaignRead,
    CollectorScanResult,
    ScanCampaignRead,
    ScanResult,
)
from app.schemas.intelligence import CampaignIntelligenceRead, ChangeType
from app.services.campaign_normalizer import normalize_campaign
from app.services.history_engine import create_snapshot, detect_changes
from app.services.intelligence_engine import (
    analyze_campaign,
    get_stored_intelligence,
)
from app.services.scoring import calculate_scores


class CollectorError(RuntimeError):
    pass


class BaseCollector(ABC):
    source_name: str
    source_url: str
    timeout_seconds: float = 25.0
    max_response_bytes: int = 5_000_000
    user_agent: str = "MilesIntelligence/0.4 (+https://github.com/dcfonsecaa/miles-intelligence)"

    def fetch(self, *, client: httpx.Client | None = None) -> str:
        owns_client = client is None
        http_client = client or httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
            },
        )
        try:
            response = http_client.get(self.source_url)
            response.raise_for_status()
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > self.max_response_bytes:
                raise CollectorError(
                    f"Resposta da fonte {self.source_name} excede o limite permitido."
                )
            if len(response.content) > self.max_response_bytes:
                raise CollectorError(
                    f"Resposta da fonte {self.source_name} excede o limite permitido."
                )
            content_type = response.headers.get("content-type", "").casefold()
            if content_type and "html" not in content_type:
                raise CollectorError(
                    f"A fonte {self.source_name} retornou conteúdo inesperado."
                )
            body = response.text.strip()
            if not body:
                raise CollectorError(f"A fonte {self.source_name} retornou conteúdo vazio.")
            if "<html" not in body.casefold() and "<!doctype html" not in body.casefold():
                raise CollectorError(
                    f"A fonte {self.source_name} retornou HTML inesperado."
                )
            return response.text
        except httpx.HTTPStatusError as exc:
            raise CollectorError(
                f"Fonte {self.source_name} respondeu HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise CollectorError(f"Falha de comunicação com a fonte {self.source_name}.") from exc
        finally:
            if owns_client:
                http_client.close()

    @abstractmethod
    def parse(self, html: str) -> list[CampaignCreate]:
        raise NotImplementedError

    def normalize(self, campaign: CampaignCreate) -> CampaignCreate:
        return normalize_campaign(campaign)

    def identify(self, db: Session, campaign: CampaignCreate) -> Campaign | None:
        return find_existing_campaign(db, campaign)

    def persist(self, db: Session, campaigns: list[CampaignCreate]) -> ScanResult:
        return persist_campaigns(campaigns, db, already_normalized=True)

    def run(
        self,
        db: Session,
        *,
        client: httpx.Client | None = None,
    ) -> CollectorScanResult:
        html = self.fetch(client=client)
        raw_campaigns = self.parse(html)
        if not raw_campaigns:
            raise CollectorError(
                f"A fonte {self.source_name} foi acessada, mas nenhuma campanha foi reconhecida."
            )
        normalized = [self.normalize(campaign) for campaign in raw_campaigns]
        result = self.persist(db, normalized)
        return CollectorScanResult(source=self.source_name, **result.model_dump())


def find_existing_campaign(db: Session, normalized: CampaignCreate) -> Campaign | None:
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


def persist_campaigns(
    detected: list[CampaignCreate],
    db: Session,
    *,
    already_normalized: bool = False,
) -> ScanResult:
    returned: list[ScanCampaignRead] = []
    inserted = updated = unchanged = errors = 0

    for payload in detected:
        try:
            with db.begin_nested():
                normalized = payload if already_normalized else normalize_campaign(payload)
                existing = find_existing_campaign(db, normalized)
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
                    if existing.campaign_key != normalized.campaign_key:
                        existing.campaign_key = normalized.campaign_key
                        db.flush()
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
