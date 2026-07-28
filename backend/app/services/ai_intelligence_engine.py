from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.schemas.intelligence import (
    CampaignAIAnalysis,
    CampaignIntelligenceRead,
    SimilarCampaignRead,
)
from app.services.intelligence_engine import analyze_campaign, get_stored_intelligence


class PredictionProvider(Protocol):
    """Extension point for a future statistical or AI prediction provider."""

    def predict(self, campaign: Campaign, peers: list[Campaign]) -> tuple[str, str]:
        ...


class NoPredictionProvider:
    def predict(self, campaign: Campaign, peers: list[Campaign]) -> tuple[str, str]:
        return (
            "not_configured",
            "Previsões ainda não estão habilitadas; a análise atual usa regras determinísticas.",
        )


class CampaignInsightEngine:
    version = "deterministic-ai-ready-v1"

    def __init__(self, prediction_provider: PredictionProvider | None = None):
        self.prediction_provider = prediction_provider or NoPredictionProvider()

    def analyze(self, db: Session, campaign: Campaign) -> CampaignAIAnalysis:
        intelligence = get_stored_intelligence(db, campaign.id) or analyze_campaign(db, campaign)
        peers = self._peers(db, campaign)
        forecast_status, forecast_message = self.prediction_provider.predict(campaign, peers)
        recommendation_code, recommendation_label, recommendation_text = (
            self._recommendation(campaign, intelligence)
        )
        return CampaignAIAnalysis(
            campaign_id=campaign.id,
            engine=self.version,
            generated_at=datetime.now(UTC),
            automatic_summary=self._summary(campaign, intelligence),
            hc_score_explanation=self._hc_score_explanation(campaign, intelligence),
            recommendation_code=recommendation_code,
            recommendation_label=recommendation_label,
            recommendation_text=recommendation_text,
            similar_campaigns=self._comparisons(campaign, peers),
            forecast_status=forecast_status,
            forecast_message=forecast_message,
        )

    @staticmethod
    def _peers(db: Session, campaign: Campaign) -> list[Campaign]:
        candidates = list(
            db.scalars(
                select(Campaign).where(
                    Campaign.id != campaign.id,
                    Campaign.campaign_type == campaign.campaign_type,
                )
            )
        )
        return sorted(
            candidates,
            key=lambda peer: (
                0 if (peer.program_name or peer.company) == (campaign.program_name or campaign.company) else 1,
                abs(peer.hc_score - campaign.hc_score),
                peer.id,
            ),
        )[:5]

    @staticmethod
    def _comparisons(
        campaign: Campaign,
        peers: list[Campaign],
    ) -> list[SimilarCampaignRead]:
        return [
            SimilarCampaignRead(
                campaign_id=peer.id,
                company=peer.company,
                program_name=peer.program_name,
                title=peer.title,
                hc_score=peer.hc_score,
                hc_score_difference=round(campaign.hc_score - peer.hc_score, 1),
                bonus_points=peer.bonus_points,
                cpm=peer.cpm,
            )
            for peer in peers
        ]

    @staticmethod
    def _summary(
        campaign: Campaign,
        intelligence: CampaignIntelligenceRead,
    ) -> str:
        program = campaign.program_name or campaign.company
        points = f"{campaign.bonus_points:,.0f}".replace(",", ".")
        cost = (
            f"custo confirmado de R$ {campaign.cost_brl:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
            if campaign.cost_status == "known" and campaign.cost_brl is not None
            else "custo ainda não confirmado"
        )
        position = {
            "above_average": "acima da média histórica",
            "below_average": "abaixo da média histórica",
            "near_average": "próxima da média histórica",
            "insufficient_data": "sem histórico comparável suficiente",
        }.get(intelligence.historical_position, "com posição histórica indefinida")
        return (
            f"{campaign.title}, do programa {program}, oferece {points} pontos, "
            f"tem {cost} e está {position}. O HC Score atual é {campaign.hc_score:.1f}."
        )

    @staticmethod
    def _hc_score_explanation(
        campaign: Campaign,
        intelligence: CampaignIntelligenceRead,
    ) -> list[str]:
        if campaign.bonus_points <= 0:
            reasons = ["Sem pontos explícitos, o cálculo aplica o HC Score base de 10,0."]
        elif campaign.cost_status != "known" or campaign.cost_brl is None:
            scale = min(100.0, campaign.bonus_points / 1000)
            reasons = [
                f"O componente de escala é {scale:.1f}, limitado a 100.",
                "Como o custo é desconhecido, o HC Score usa somente 30% do componente de escala.",
                "CPM e avaliação financeira permanecem indisponíveis.",
            ]
        else:
            scale = min(100.0, campaign.bonus_points / 1000)
            reasons = [
                f"O componente de escala é {scale:.1f}, limitado a 100.",
                "Com custo conhecido, o cálculo combina 70% de valor por CPM e 30% de escala.",
                f"O CPM confirmado usado no cálculo é {campaign.cpm:.2f}."
                if campaign.cpm is not None
                else "O CPM não pôde ser calculado.",
            ]
        reasons.extend(intelligence.reasons[:2])
        return reasons

    @staticmethod
    def _recommendation(
        campaign: Campaign,
        intelligence: CampaignIntelligenceRead,
    ) -> tuple[str, str, str]:
        if campaign.cost_status != "known" or campaign.cost_brl is None:
            if intelligence.historical_position == "above_average" or intelligence.is_points_record:
                return (
                    "above_average",
                    "Promoção acima da média",
                    "O volume de pontos se destaca, mas aguarde a confirmação do custo e do regulamento antes de decidir.",
                )
            return (
                "wait",
                "Aguarde",
                "Confirme custo, elegibilidade e prazo; sem esses dados não há recomendação financeira definitiva.",
            )
        if intelligence.recommendation_level.value in {"attractive", "potentially_attractive"}:
            return (
                "worth_considering",
                "Vale aproveitar",
                "Os dados financeiros e históricos são favoráveis; confirme o regulamento antes da contratação.",
            )
        if intelligence.recommendation_level.value == "unattractive":
            return (
                "wait",
                "Aguarde",
                "O custo está desfavorável frente ao histórico comparável; procure uma condição melhor.",
            )
        if intelligence.historical_position == "above_average":
            return (
                "above_average",
                "Promoção acima da média",
                "A campanha supera o volume histórico comparável, mas ainda deve ser avaliada em conjunto com o CPM.",
            )
        return (
            "monitor",
            "Monitore",
            "A campanha não apresenta evidência suficiente para uma decisão imediata.",
        )


campaign_insight_engine = CampaignInsightEngine()
