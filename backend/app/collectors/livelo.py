from app.collectors.base import BaseCollector
from app.schemas.campaign import CampaignCreate
from app.services.livelo_collector import (
    LIVELO_REGULATIONS_URL,
    parse_livelo_campaigns,
)


class LiveloCollector(BaseCollector):
    source_name = "Livelo"
    source_url = LIVELO_REGULATIONS_URL

    def parse(self, html: str) -> list[CampaignCreate]:
        return parse_livelo_campaigns(html)
