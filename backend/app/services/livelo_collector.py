from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

from app.schemas.campaign import CampaignCreate

LIVELO_REGULATIONS_URL = "https://www.livelo.com.br/regulamentos-ativos"
DEFAULT_TIMEOUT_SECONDS = 25.0

_PERIOD_RE = re.compile(
    r"(?:per[ií]odo\s*:?\s*)?"
    r"(?P<start>\d{1,2}/\d{1,2}/\d{2,4})"
    r"\s*(?:a|até|-)\s*"
    r"(?P<end>\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)
_POINTS_RE = re.compile(r"(?P<value>\d{1,3}(?:[.\s]\d{3})+|\d+)\s*(?:k\s*)?(?:pts?|pontos)", re.IGNORECASE)
_K_POINTS_RE = re.compile(r"(?P<value>\d+(?:[,.]\d+)?)\s*k\s*(?:pts?|pontos)?", re.IGNORECASE)


@dataclass(frozen=True)
class LiveloCollectionResult:
    campaigns: list[CampaignCreate]
    fetched_at: datetime
    source_url: str = LIVELO_REGULATIONS_URL


def _clean_text(value: str) -> str:
    return " ".join(value.split()).strip()


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


def _extract_bonus_points(text: str) -> int:
    values: list[int] = []
    for match in _POINTS_RE.finditer(text):
        raw = re.sub(r"[.\s]", "", match.group("value"))
        try:
            values.append(int(raw))
        except ValueError:
            pass

    for match in _K_POINTS_RE.finditer(text):
        raw = match.group("value").replace(",", ".")
        try:
            values.append(int(float(raw) * 1000))
        except ValueError:
            pass

    return max(values, default=0)


def _is_campaign_heading(tag: Tag) -> bool:
    if tag.name not in {"h2", "h3", "h4"}:
        return False
    title = _clean_text(tag.get_text(" ", strip=True))
    if len(title) < 8:
        return False
    excluded = {
        "programa de pontos livelo",
        "regulamento shopping livelo",
        "clube livelo",
        "usar pontos",
        "juntar pontos",
        "transferir seus pontos",
        "institucional",
        "comprar pontos",
        "para empresas",
        "aplicativo",
        "formas de pagamento",
        "redes sociais",
        "siga a livelo",
        "selos",
    }
    return title.casefold() not in excluded


def _collect_block(heading: Tag) -> tuple[str, str | None]:
    fragments: list[str] = []
    regulation_url: str | None = None

    for sibling in heading.next_siblings:
        if isinstance(sibling, Tag) and sibling.name in {"h2", "h3", "h4"}:
            break
        if not isinstance(sibling, Tag):
            continue

        text = _clean_text(sibling.get_text(" ", strip=True))
        if text:
            fragments.append(text)

        if regulation_url is None:
            link = sibling.find("a", href=True)
            if link:
                regulation_url = urljoin(LIVELO_REGULATIONS_URL, link["href"])

    return " ".join(fragments), regulation_url


def parse_livelo_campaigns(html: str) -> list[CampaignCreate]:
    soup = BeautifulSoup(html, "html.parser")
    campaigns: list[CampaignCreate] = []
    seen: set[str] = set()

    for heading in soup.find_all(_is_campaign_heading):
        title = _clean_text(heading.get_text(" ", strip=True))
        block_text, regulation_url = _collect_block(heading)
        combined = _clean_text(f"{title} {block_text}")
        start_date, end_date = _extract_period(combined)
        bonus_points = _extract_bonus_points(title)

        # A página possui regulamentos institucionais permanentes. Para o radar inicial,
        # mantemos apenas itens com período, pontuação explícita ou linguagem promocional.
        promotional_terms = ("promo", "adesão", "off", "cupom", "pontos de volta", "campanha")
        is_promotional = any(term in combined.casefold() for term in promotional_terms)
        if not (start_date or end_date or bonus_points or is_promotional):
            continue

        source_url = regulation_url or f"{LIVELO_REGULATIONS_URL}#{len(campaigns) + 1}"
        dedupe_key = source_url.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        period_summary = ""
        if start_date and end_date:
            period_summary = f" Período identificado: {start_date:%d/%m/%Y} a {end_date:%d/%m/%Y}."

        campaigns.append(
            CampaignCreate(
                company="Livelo",
                title=title,
                source_url=source_url,
                category="programas de pontos",
                bonus_points=bonus_points,
                cost_brl=0.0,
                summary=(
                    "Campanha detectada automaticamente na página oficial de regulamentos ativos da Livelo."
                    f"{period_summary} Confirme custos, elegibilidade e condições no regulamento oficial."
                ),
            )
        )

    return campaigns


def collect_livelo_campaigns(*, client: httpx.Client | None = None) -> LiveloCollectionResult:
    owns_client = client is None
    http_client = client or httpx.Client(
        timeout=DEFAULT_TIMEOUT_SECONDS,
        follow_redirects=True,
        headers={
            "User-Agent": "MilesIntelligence/0.2 (+https://github.com/dcfonsecaa/miles-intelligence)",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
        },
    )

    try:
        response = http_client.get(LIVELO_REGULATIONS_URL)
        response.raise_for_status()
        campaigns = parse_livelo_campaigns(response.text)
        if not campaigns:
            raise RuntimeError("A página da Livelo foi acessada, mas nenhuma campanha foi reconhecida.")
        return LiveloCollectionResult(campaigns=campaigns, fetched_at=datetime.utcnow())
    finally:
        if owns_client:
            http_client.close()
