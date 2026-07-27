from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreResult:
    cpm: float | None
    hc_score: float
    anomaly_score: float


def calculate_scores(*, bonus_points: int, cost_brl: float, historical_avg_cpm: float = 28.0) -> ScoreResult:
    if bonus_points <= 0:
        return ScoreResult(cpm=None, hc_score=10.0, anomaly_score=0.0)

    cpm = round((cost_brl / bonus_points) * 1000, 2) if cost_brl > 0 else 0.0

    if cpm == 0:
        value_score = 100.0
    else:
        value_score = max(0.0, min(100.0, 100 - (cpm / 0.5)))

    scale_score = min(100.0, bonus_points / 1000)
    hc_score = round((value_score * 0.7) + (scale_score * 0.3), 1)

    if cpm == 0:
        anomaly_score = min(100.0, 70 + (bonus_points / 2000))
    else:
        deviation = max(0.0, historical_avg_cpm - cpm)
        anomaly_score = min(100.0, (deviation / historical_avg_cpm) * 100 + scale_score * 0.25)

    return ScoreResult(cpm=cpm, hc_score=round(hc_score, 1), anomaly_score=round(anomaly_score, 1))
