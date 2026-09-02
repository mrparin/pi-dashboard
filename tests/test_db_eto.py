from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.db import Database


def sample(timestamp_ms: int, hourly_rate: float) -> dict:
    values = {
        "timestamp_ms": timestamp_ms,
        "node": "node01",
        "zone": "zone01",
        "eto_mm_h_est": hourly_rate,
    }
    optional = {
        "air_temp", "air_humi", "lux", "wind_speed_avg5m", "wind_dir_deg",
        "wind_dir_th", "soil_temp", "soil_humi", "ec", "ph", "n", "p", "k",
        "es_kpa", "ea_kpa", "vpd_kpa", "solar_wm2_est", "solar_mj_m2_h_est",
        "eto_mm_day_est", "vpd_status", "vpd_message", "vpd_action", "ph_status",
        "ph_message", "ph_action",
    }
    values.update({key: None for key in optional if key not in values})
    return values


def test_daily_eto_is_integrated_and_long_gaps_are_not_filled(tmp_path) -> None:
    db = Database(str(tmp_path / "test.db"), max_eto_gap_minutes=60)
    start = 1_788_306_000_000
    first = sample(start, 0.2)
    second = sample(start + (30 * 60 * 1000), 0.4)
    after_gap = sample(start + (150 * 60 * 1000), 0.5)

    db.insert_sample(first)
    db.insert_sample(second)
    db.insert_sample(after_gap)

    assert first["eto_mm_day_est"] == 0.0
    assert second["eto_mm_day_est"] == pytest.approx(0.15)
    assert after_gap["eto_mm_day_est"] == pytest.approx(0.15)
    db.close()


def test_daily_eto_returns_last_observed_total_for_each_thai_day(tmp_path) -> None:
    timezone = ZoneInfo("Asia/Bangkok")
    today = datetime.now(timezone).replace(hour=8, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    db = Database(str(tmp_path / "daily.db"))

    rows = [
        sample(int(yesterday.timestamp() * 1000), 0.2),
        sample(int((yesterday + timedelta(hours=1)).timestamp() * 1000), 0.4),
        sample(int(today.timestamp() * 1000), 0.1),
        sample(int((today + timedelta(hours=1)).timestamp() * 1000), 0.3),
    ]
    for row in rows:
        db.insert_sample(row)

    points = db.get_eto_daily(days=2)

    assert [point["date"] for point in points] == [yesterday.date().isoformat(), today.date().isoformat()]
    assert [point["value"] for point in points] == pytest.approx([0.3, 0.2])
    db.close()
