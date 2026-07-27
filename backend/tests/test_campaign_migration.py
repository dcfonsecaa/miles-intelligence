from sqlalchemy import create_engine, inspect, text

from app.core.campaign_migration import migrate_campaign_model_v2


def test_migration_preserves_legacy_ids_and_converts_livelo_zero_cost(tmp_path):
    database_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE campaigns (
                    id INTEGER PRIMARY KEY,
                    company VARCHAR(120) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    source_url VARCHAR(500) NOT NULL UNIQUE,
                    category VARCHAR(80),
                    bonus_points INTEGER,
                    cost_brl FLOAT,
                    cpm FLOAT,
                    hc_score FLOAT,
                    anomaly_score FLOAT,
                    status VARCHAR(30),
                    summary TEXT,
                    detected_at DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO campaigns (
                    id, company, title, source_url, category, bonus_points, cost_brl,
                    cpm, hc_score, anomaly_score, status, summary, detected_at
                ) VALUES (
                    41, 'Livelo', '[UPGRADE] Top - 96k pontos em 12 meses - anual',
                    'https://assets.example.com/top.pdf', 'programas de pontos', 96000,
                    0, 0, 98, 100, 'detected', '', '2026-07-27 10:00:00'
                )
                """
            )
        )

    migrate_campaign_model_v2(engine)
    migrate_campaign_model_v2(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("campaigns")}
    assert {"campaign_key", "cost_status", "normalized_title", "monthly_points"}.issubset(columns)
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT id, cost_brl, cost_status, cpm, monthly_points FROM campaigns")
        ).mappings().all()
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == 41
    assert row["cost_brl"] is None
    assert row["cost_status"] == "unknown"
    assert row["cpm"] is None
    assert row["monthly_points"] == 8000
