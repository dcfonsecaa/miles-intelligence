from app.services.scoring import calculate_scores


def test_calculates_cpm():
    result = calculate_scores(bonus_points=100_000, cost_brl=1_200)
    assert result.cpm == 12.0
    assert result.hc_score > 80
    assert result.anomaly_score > 50


def test_free_campaign_receives_high_score():
    result = calculate_scores(bonus_points=30_000, cost_brl=0)
    assert result.cpm == 0
    assert result.hc_score >= 75


def test_campaign_without_points_is_low_value():
    result = calculate_scores(bonus_points=0, cost_brl=100)
    assert result.cpm is None
    assert result.hc_score == 10
