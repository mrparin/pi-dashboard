from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _optional_float(name: str) -> float | None:
    value = os.getenv(name, "").strip()
    return float(value) if value else None


@dataclass(frozen=True)
class Settings:
    mqtt_host: str = os.getenv("MQTT_HOST", "sci-iot.ddns.net")
    mqtt_port: int = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_topic: str = os.getenv("MQTT_TOPIC", "durian_farm1/node_sensor")
    mqtt_qos: int = int(os.getenv("MQTT_QOS", "1"))

    db_path: str = os.getenv("DB_PATH", "./data/durian_dashboard.db")
    retain_days: int = int(os.getenv("RETAIN_DAYS", "90"))

    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8080"))
    refresh_seconds: int = int(os.getenv("REFRESH_SECONDS", "3"))
    frontend_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3001").split(",")
        if origin.strip()
    )

    tmd_access_token: str = os.getenv("TMD_ACCESS_TOKEN", "").strip()

    # Required for a complete FAO-56 hourly ET0 radiation calculation.
    station_latitude: float | None = _optional_float("STATION_LATITUDE")
    station_longitude: float | None = _optional_float("STATION_LONGITUDE")
    station_altitude_m: float = float(os.getenv("STATION_ALTITUDE_M", "0"))
    station_timezone: str = os.getenv("STATION_TIMEZONE", "Asia/Bangkok")
    wind_sensor_height_m: float = float(os.getenv("WIND_SENSOR_HEIGHT_M", "2"))
    lux_per_wm2: float = float(os.getenv("LUX_PER_WM2", "120"))
    eto_max_gap_minutes: int = int(os.getenv("ETO_MAX_GAP_MINUTES", "60"))


settings = Settings()
