import pytest

from app.schemas.campaign import CampaignCreate, CampaignType, CostStatus, Modality
from app.services.campaign_normalizer import (
    build_campaign_key,
    extract_bonus_points,
    extract_duration_months,
    normalize_campaign,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("Receba 96.000 pontos", 96_000),
        ("Ganhe 96 mil pontos", 96_000),
        ("Bônus de 96k pontos", 96_000),
        ("Clube com 74k pts", 74_000),
    ),
)
def test_extracts_supported_points_formats(text, expected):
    assert extract_bonus_points(text) == expected


@pytest.mark.parametrize("text", ("em 12 meses", "por 12 meses", "durante 12 meses"))
def test_extracts_supported_duration_formats(text):
    assert extract_duration_months(text) == 12


def test_normalizes_upgrade_annual_campaign():
    normalized = normalize_campaign(
        CampaignCreate(
            company="Livelo",
            title="[UPGRADE] Top - 96.000 pontos extras em 12 meses - anual",
            source_url="https://assets.example.com/top.pdf",
        )
    )

    assert normalized.program_name == "Clube Livelo"
    assert normalized.campaign_type == CampaignType.UPGRADE
    assert normalized.modality == Modality.ANNUAL
    assert normalized.bonus_points == 96_000
    assert normalized.duration_months == 12
    assert normalized.monthly_points == 8_000
    assert normalized.cost_brl is None
    assert normalized.cost_status == CostStatus.UNKNOWN
    assert normalized.extraction_confidence.value == "high"


def test_identifies_subscription():
    normalized = normalize_campaign(
        CampaignCreate(
            company="Livelo",
            title="[ADESÃO] Clube Mega mensal com 12k pontos",
            source_url="https://assets.example.com/mega.pdf",
        )
    )
    assert normalized.campaign_type == CampaignType.SUBSCRIPTION
    assert normalized.modality == Modality.MONTHLY


def test_campaign_key_is_stable():
    arguments = {
        "company": "Livelo",
        "normalized_title": "Campanha Top",
        "regulation_url": "https://assets.example.com/top.pdf",
        "campaign_type": CampaignType.UPGRADE,
        "modality": Modality.ANNUAL,
    }
    assert build_campaign_key(**arguments) == build_campaign_key(**arguments)


def test_different_titles_on_same_page_have_different_keys():
    first = normalize_campaign(
        CampaignCreate(company="Livelo", title="Upgrade Top 96k pontos", source_url="https://same.example/page")
    )
    second = normalize_campaign(
        CampaignCreate(company="Livelo", title="Adesão Mega 74k pontos", source_url="https://same.example/page")
    )
    assert first.source_url == second.source_url
    assert first.campaign_key != second.campaign_key
