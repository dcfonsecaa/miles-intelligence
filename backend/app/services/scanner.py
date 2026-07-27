from app.schemas.campaign import CampaignCreate


# Primeira fonte simulada. A próxima etapa substituirá esta lista por conectores reais.
DEMO_CAMPAIGNS = [
    CampaignCreate(
        company="Health Choice",
        title="Campanha histórica de aquisição com alta pontuação",
        source_url="demo://health-choice/historical-case",
        category="seguros",
        bonus_points=100_000,
        cost_brl=1_200.00,
        summary="Caso de referência usado para validar o detector de campanhas fora do padrão.",
    ),
    CampaignCreate(
        company="Banco Exemplo",
        title="Abra a conta e receba 30.000 pontos",
        source_url="demo://bank-example/account-30000",
        category="bancos",
        bonus_points=30_000,
        cost_brl=0.0,
        summary="Campanha simulada para testar campanhas com custo direto zero.",
    ),
    CampaignCreate(
        company="Clube Exemplo",
        title="Assinatura anual com 24.000 pontos",
        source_url="demo://club-example/annual-24000",
        category="clubes",
        bonus_points=24_000,
        cost_brl=960.00,
        summary="Campanha simulada com custo por milheiro elevado para comparação.",
    ),
]


def collect_demo_campaigns() -> list[CampaignCreate]:
    return DEMO_CAMPAIGNS.copy()
