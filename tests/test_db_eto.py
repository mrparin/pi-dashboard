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
