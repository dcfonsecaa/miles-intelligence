from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from app.collectors.base import BaseCollector
from app.schemas.campaign import CampaignCreate, CampaignType, CostStatus

_BONUS_RE = re.compile(r"(\d{1,3})\s*%\s*(?:de\s+)?b[oô]nus", re.IGNORECASE)
_PERIOD_RE = re.compile(
    r"(\d{1,2}/\d{1,2}/\d{2,4})\s*(?:a|até|e|-)\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)
_VALID_UNTIL_RE = re.compile(
    r"v[aá]lid[ao]\s+at[eé]\s+(\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)
_CREDIT_RE = re.compile(
    r"(?:creditad[ao]s?|cr[eé]dito)[^.]{0,60}?(?:at[eé]\s+)?(\d+)\s+"
    r"(?:horas?|dias?\s+(?:úteis|uteis|corridos))",
    re.IGNORECASE,
)
_LIMIT_RE = re.compile(
    r"limitad[ao]s?\s+a\s+([\d.]+\s+(?:milhas|pontos))",
    re.IGNORECASE,
)
_PARTNERS = (
    "Esfera",
    "Livelo",
    "KMV",
    "Itaú",
    "Itaú Unibanco",
    "Bradesco",
    "Banco do Brasil",
    "Caixa",
    "Santander",
    "Inter",
    "Sicredi",
    "C6 Bank",
)


def _clean(value: str) -> str:
    return " ".join(value.split()).strip()


def _parse_date(raw: str):
    for date_format in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw, date_format).date()
        except ValueError:
            continue
    return None


def _period(text: str):
    match = _PERIOD_RE.search(text)
    if match:
        return _parse_date(match.group(1)), _parse_date(match.group(2))
    valid_until = _VALID_UNTIL_RE.search(text)
    return (None, _parse_date(valid_until.group(1))) if valid_until else (None, None)


def _campaign_type(text: str) -> CampaignType:
    folded = text.casefold()
    if "transf" in folded and ("ponto" in folded or "milha" in folded):
        return CampaignType.TRANSFER_BONUS
    if ("compr" in folded or "desconto" in folded) and "milha" in folded:
        return CampaignType.POINTS_PURCHASE
    if "clube latam pass" in folded and any(
        term in folded for term in ("assine", "adesão", "adesao", "plano")
    ):
        return CampaignType.SUBSCRIPTION
    if "cartão latam pass itaú" in folded or "cartao latam pass itau" in folded:
        return CampaignType.CARD_ACQUISITION
    if "abra sua conta" in folded or "abertura de conta" in folded:
        return CampaignType.ACCOUNT_OPENING
    return CampaignType.OTHER


def _partner(text: str) -> str | None:
    folded = text.casefold()
    for partner in _PARTNERS:
        if partner.casefold() in folded:
            return partner
    return None


class LatamPassCollector(BaseCollector):
    source_name = "LATAM Pass"
    source_url = "https://latampass.latam.com/pt_br/ofertas"

    def parse(self, html: str) -> list[CampaignCreate]:
        soup = BeautifulSoup(html, "html.parser")
        campaigns: list[CampaignCreate] = []
        seen: set[tuple[str, str]] = set()

        for link in soup.find_all("a", href=True):
            regulation_url = urljoin(self.source_url, link["href"])
            parsed = urlparse(regulation_url)
            if parsed.netloc.casefold() not in {
                "latampass.latam.com",
                "www.latampass.latam.com",
                "latamairlines.com",
                "www.latamairlines.com",
            }:
                continue
            if not any(part in parsed.path.casefold() for part in ("/promocao", "/oferta")):
                continue

            container = link.find_parent(["article", "li"]) or link.parent
            if not isinstance(container, Tag):
                continue
            text = _clean(container.get_text(" ", strip=True))
            heading = container.find(["h1", "h2", "h3", "h4"])
            title = _clean(heading.get_text(" ", strip=True)) if heading else _clean(
                link.get_text(" ", strip=True)
            )
            if len(title) < 5 or len(text) < 12:
                continue

            identity = (title.casefold(), regulation_url.casefold())
            if identity in seen:
                continue
            seen.add(identity)

            bonus_values = [int(value) for value in _BONUS_RE.findall(text)]
            bonus_percent = max(bonus_values, default=None)
            registration_required = bool(
                re.search(r"cadastre-se|se cadastrar|ative a promo", text, re.IGNORECASE)
            )
            club_mentioned = "clube latam pass" in text.casefold()
            start_date, end_date = _period(text)
            credit_match = _CREDIT_RE.search(text)
            limit_match = _LIMIT_RE.search(text)
            notes = [
                "Dados extraídos de uma página oficial do LATAM Pass.",
                f"bonus_percent={bonus_percent}" if bonus_percent is not None else None,
                f"registration_required={str(registration_required).lower()}",
                f"club_latam_pass_mentioned={str(club_mentioned).lower()}",
                f"credit_deadline={_clean(credit_match.group(0))}" if credit_match else None,
                f"cpf_limit={_clean(limit_match.group(1))}" if limit_match else None,
            ]

            campaigns.append(
                CampaignCreate(
                    company="LATAM Pass",
                    program_name="LATAM Pass",
                    campaign_type=_campaign_type(f"{title} {text}"),
                    partner_name=_partner(f"{title} {text}"),
                    title=title,
                    source_url=self.source_url,
                    regulation_url=regulation_url,
                    category="programas de fidelidade",
                    cost_brl=None,
                    cost_status=CostStatus.UNKNOWN,
                    start_date=start_date,
                    end_date=end_date,
                    eligibility=text,
                    summary=text,
                    extraction_notes="; ".join(item for item in notes if item),
                )
            )
        return campaigns
