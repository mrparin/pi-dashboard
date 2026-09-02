import datetime as dt

import pytest

from app.config import Settings
from app.logic import (
    calc_fao56_hourly_eto,
    normalize_payload,
    parse_sensor_time,
    wind_speed_at_2m,
)


def test_fao56_example_19_daytime() -> None:
    """FAO-56 Example 19 reports 0.63 mm/h for 14:00-15:00."""
    eto = calc_fao56_hourly_eto(
        air_temp_c=38.0,
        vpd_kpa=3.180,
        wind_speed_ms=3.3,
        net_radiation_mj_m2_h=1.749,
        soil_heat_flux_mj_m2_h=0.175,
        altitude_m=8.0,
    )
    assert eto == pytest.approx(0.63, abs=0.01)


def test_wind_speed_is_normalized_from_10m_to_2m() -> None:
    assert wind_speed_at_2m(3.2, 10.0) == pytest.approx(2.4, abs=0.05)


def test_sensor_time_is_interpreted_in_thailand_timezone() -> None:
    timestamp_ms = parse_sensor_time("02/09/2026 08:30:00", "Asia/Bangkok")
    utc = dt.datetime.fromtimestamp(timestamp_ms / 1000.0, dt.timezone.utc)
    assert utc == dt.datetime(2026, 9, 2, 1, 30, tzinfo=dt.timezone.utc)


def test_eto_requires_station_coordinates() -> None:
    sample = normalize_payload(
        {
            "time": "02/09/2026 12:00:00",
            "node": "node01",
            "zone": "zone01",
            "env": {
                "air_temp": 32.0,
                "air_humi": 65.0,
                "lux": 60000,
                "wind_speed_avg5m": 1.5,
            },
            "npk": {},
        },
        Settings(station_latitude=None, station_longitude=None),
    )
    assert "eto_mm_h_est" not in sample


def test_payload_with_coordinates_produces_nonnegative_hourly_eto() -> None:
    sample = normalize_payload(
        {
            "time": "02/09/2026 12:00:00",
            "node": "node01",
            "zone": "zone01",
            "env": {
                "air_temp": 32.0,
                "air_humi": 65.0,
                "lux": 60000,
                "wind_speed_avg5m": 1.5,
            },
            "npk": {},
        },
        Settings(station_latitude=12.7, station_longitude=101.1, station_altitude_m=30),
    )
    assert sample["eto_mm_h_est"] >= 0
