from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime

from app.schemas.campaign import (
    CampaignCreate,
    CampaignType,
    CostStatus,
    ExtractionConfidence,
    Modality,
)

_POINT_PATTERNS = (
    re.compile(r"(?P<value>\d{1,3}(?:[.\s]\d{3})+|\d+)\s*(?:pontos|pts?)", re.IGNORECASE),
    re.compile(r"(?P<value>\d+(?:[,.]\d+)?)\s*(?:mil|k)\s*(?:pontos|pts?)?", re.IGNORECASE),
)
_DURATION_RE = re.compile(r"(?:em|por|durante)\s+(?P<months>\d{1,3})\s*(?:meses|mês|m\b)", re.IGNORECASE)
_PERIOD_RE = re.compile(
    r"(?P<start>\d{1,2}/\d{1,2}/\d{2,4})\s*(?:a|até|-)\s*(?P<end>\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)


def _ascii_fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def normalize_title(value: str) -> str:
    return " ".join(value.split()).strip()


def extract_bonus_points(text: str) -> int:
    values: list[int] = []
    for index, pattern in enumerate(_POINT_PATTERNS):
        for match in pattern.finditer(text):
            raw = match.group("value").replace(" ", "")
            if index == 0:
                raw = raw.replace(".", "")
                multiplier = 1
            else:
                raw = raw.replace(",", ".")
                multiplier = 1000
            try:
                values.append(int(float(raw) * multiplier))
            except ValueError:
                continue
    return max(values, default=0)


def extract_duration_months(text: str) -> int | None:
    match = _DURATION_RE.search(text)
    return int(match.group("months")) if match else None


def detect_campaign_type(text: str) -> CampaignType:
    folded = _ascii_fold(text)
    rules = (
        (CampaignType.UPGRADE, ("upgrade",)),
        (CampaignType.TRANSFER_BONUS, ("transferencia bonificada", "bonus de transferencia")),
        (CampaignType.POINTS_PURCHASE, ("compra de pontos", "comprar pontos")),
        (CampaignType.SUBSCRIPTION, ("adesao", "assinatura")),
        (CampaignType.CARD_ACQUISITION, ("cartao",)),
        (CampaignType.ACCOUNT_OPENING, ("abertura de conta", "abra a conta")),
        (CampaignType.INSURANCE, ("seguro",)),
        (CampaignType.INVESTMENT, ("investimento",)),
        (CampaignType.SHOPPING, ("shopping", "compre e ganhe")),
        (CampaignType.TRAVEL, ("viagem", "passagem")),
    )
    for campaign_type, terms in rules:
        if any(term in folded for term in terms):
            return campaign_type
    return CampaignType.OTHER


def detect_modality(text: str) -> Modality:
    folded = _ascii_fold(text)
    if "anual" in folded:
        return Modality.ANNUAL
    if "mensal" in folded:
        return Modality.MONTHLY
    if "recorrente" in folded:
        return Modality.RECURRING
    if "adesao unica" in folded or "unica adesao" in folded:
        return Modality.ONE_TIME
    return Modality.UNKNOWN


def _parse_date(value: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _extract_period(text: str) -> tuple[date | None, date | None]:
    match = _PERIOD_RE.search(text)
    if not match:
        return None, None
    return _parse_date(match.group("start")), _parse_date(match.group("end"))


def build_campaign_key(
    *,
    company: str,
    normalized_title: str,
    regulation_url: str | None,
    campaign_type: CampaignType | str,
    modality: Modality | str,
) -> str:
    parts = (
        _ascii_fold(company),
        _ascii_fold(normalized_title),
        (regulation_url or "").strip().casefold(),
        str(getattr(campaign_type, "value", campaign_type)),
        str(getattr(modality, "value", modality)),
    )
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def normalize_campaign(payload: CampaignCreate) -> CampaignCreate:
    raw_payload = payload.model_dump(mode="json")
    title = normalize_title(payload.title)
    combined = normalize_title(f"{title} {payload.summary}")
    company_is_livelo = _ascii_fold(payload.company) == "livelo"

    bonus_points = extract_bonus_points(title) or payload.bonus_points
    duration_months = payload.duration_months or extract_duration_months(combined)
    monthly_points = payload.monthly_points
    if monthly_points is None and duration_months and bonus_points:
        monthly_points = round(bonus_points / duration_months)

    campaign_type = (
        payload.campaign_type
        if payload.campaign_type != CampaignType.OTHER
        else detect_campaign_type(title)
    )
    modality = payload.modality if payload.modality != Modality.UNKNOWN else detect_modality(title)
    start_date, end_date = _extract_period(combined)
    start_date = payload.start_date or start_date
    end_date = payload.end_date or end_date

    regulation_url = payload.regulation_url
    source_url = payload.source_url
    if company_is_livelo:
        regulation_url = regulation_url or payload.source_url
        source_url = "https://www.livelo.com.br/regulamentos-ativos"

    cost_status = payload.cost_status
    cost_brl = payload.cost_brl
    if company_is_livelo and (cost_status == CostStatus.UNKNOWN or cost_brl == 0):
        cost_status = CostStatus.UNKNOWN
        cost_brl = None
    elif cost_brl is not None and cost_status == CostStatus.UNKNOWN:
        cost_status = CostStatus.KNOWN
    elif cost_brl is None:
        cost_status = CostStatus.UNKNOWN

    confidence_signals = sum(
        value is not None and value != CampaignType.OTHER and value != Modality.UNKNOWN
        for value in (bonus_points or None, duration_months, campaign_type, modality, regulation_url)
    )
    confidence = (
        ExtractionConfidence.HIGH
        if confidence_signals >= 4
        else ExtractionConfidence.MEDIUM
        if confidence_signals >= 2
        else ExtractionConfidence.LOW
    )
    normalized_title = normalize_title(title)
    campaign_key = build_campaign_key(
        company=payload.company,
        normalized_title=normalized_title,
        regulation_url=regulation_url,
        campaign_type=campaign_type,
        modality=modality,
    )

    return payload.model_copy(
        update={
            "program_name": payload.program_name or ("Clube Livelo" if company_is_livelo else None),
            "campaign_type": campaign_type,
            "modality": modality,
            "normalized_title": normalized_title,
            "source_url": source_url,
            "regulation_url": regulation_url,
            "bonus_points": bonus_points,
            "duration_months": duration_months,
            "monthly_points": monthly_points,
            "start_date": start_date,
            "end_date": end_date,
            "cost_brl": cost_brl,
            "cost_status": cost_status,
            "extraction_confidence": confidence,
            "campaign_key": campaign_key,
            "raw_data": json.dumps(raw_payload, ensure_ascii=False, sort_keys=True),
        }
    )
