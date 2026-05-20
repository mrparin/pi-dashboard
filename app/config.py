from __future__ import annotations

import os
from dataclasses import dataclass


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


settings = Settings()
