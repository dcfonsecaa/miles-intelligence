from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.collectors.base import BaseCollector
from app.schemas.campaign import CampaignCreate, CostStatus


class EsferaCollector(BaseCollector):
    source_name = "Esfera"
    source_url = "https://www.esfera.com.vc/termos-e-condicoes"

    def parse(self, html: str) -> list[CampaignCreate]:
        soup = BeautifulSoup(html, "html.parser")
        campaigns: list[CampaignCreate] = []
        seen: set[tuple[str, str]] = set()

        for heading in soup.find_all(["h2", "h3", "h4"]):
            title = " ".join(heading.get_text(" ", strip=True).split())
            folded = title.casefold()
            if len(title) < 8 or not any(
                term in folded
                for term in ("campanha", "promo", "pontos", "clube", "compra", "transfer")
            ):
                continue

            fragments: list[str] = []
            regulation_url = None
            partner_name = heading.get("data-partner")
            for sibling in heading.next_siblings:
                if isinstance(sibling, Tag) and sibling.name in {"h2", "h3", "h4"}:
                    break
                if not isinstance(sibling, Tag):
                    continue
                text = " ".join(sibling.get_text(" ", strip=True).split())
                if text:
                    fragments.append(text)
                if regulation_url is None:
                    link = sibling if sibling.name == "a" and sibling.get("href") else sibling.find(
                        "a", href=True
                    )
                    if link:
                        regulation_url = urljoin(self.source_url, link["href"])
                if partner_name is None and sibling.get("data-partner"):
                    partner_name = sibling.get("data-partner")

            summary = " ".join(fragments)
            identity = (title.casefold(), (regulation_url or "").casefold())
            if identity in seen:
                continue
            seen.add(identity)

            campaigns.append(
                CampaignCreate(
                    company="Esfera",
                    program_name="Esfera",
                    title=title,
                    source_url=self.source_url,
                    regulation_url=regulation_url,
                    partner_name=partner_name,
                    category="programas de pontos",
                    cost_brl=None,
                    cost_status=CostStatus.UNKNOWN,
                    eligibility=summary or None,
                    summary=summary,
                    extraction_notes=(
                        "Dados extraídos da página oficial da Esfera; confirme condições no regulamento."
                    ),
                )
            )
        return campaigns
