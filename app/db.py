from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_ms INTEGER NOT NULL,
    node TEXT NOT NULL,
    zone TEXT NOT NULL,
    air_temp REAL,
    air_humi REAL,
    lux REAL,
    wind_speed_avg5m REAL,
    wind_dir_deg REAL,
    wind_dir_th TEXT,
    soil_temp REAL,
    soil_humi REAL,
    ec REAL,
    ph REAL,
    n REAL,
    p REAL,
    k REAL,
    es_kpa REAL,
    ea_kpa REAL,
    vpd_kpa REAL,
    solar_wm2_est REAL,
    solar_mj_m2_h_est REAL,
    eto_mm_h_est REAL,
    eto_mm_day_est REAL,
    vpd_status TEXT,
    vpd_message TEXT,
    vpd_action TEXT,
    ph_status TEXT,
    ph_message TEXT,
    ph_action TEXT
);
CREATE INDEX IF NOT EXISTS idx_samples_ts ON samples(timestamp_ms);
CREATE INDEX IF NOT EXISTS idx_samples_node_zone_ts ON samples(node, zone, timestamp_ms);
"""


class Database:
    def __init__(self, db_path: str) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._conn:
            self._conn.executescript(SCHEMA_SQL)
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def insert_sample(self, sample: dict[str, Any]) -> None:
        sql = """
        INSERT INTO samples (
            timestamp_ms, node, zone, air_temp, air_humi, lux, wind_speed_avg5m,
            wind_dir_deg, wind_dir_th, soil_temp, soil_humi, ec, ph, n, p, k,
            es_kpa, ea_kpa, vpd_kpa, solar_wm2_est, solar_mj_m2_h_est,
            eto_mm_h_est, eto_mm_day_est, vpd_status, vpd_message, vpd_action,
            ph_status, ph_message, ph_action
        ) VALUES (
            :timestamp_ms, :node, :zone, :air_temp, :air_humi, :lux, :wind_speed_avg5m,
            :wind_dir_deg, :wind_dir_th, :soil_temp, :soil_humi, :ec, :ph, :n, :p, :k,
            :es_kpa, :ea_kpa, :vpd_kpa, :solar_wm2_est, :solar_mj_m2_h_est,
            :eto_mm_h_est, :eto_mm_day_est, :vpd_status, :vpd_message, :vpd_action,
            :ph_status, :ph_message, :ph_action
        )
        """
        with self._lock:
            with self._conn:
                self._conn.execute(sql, sample)

    def get_latest(self) -> dict[str, Any] | None:
        sql = "SELECT * FROM samples ORDER BY timestamp_ms DESC LIMIT 1"
        with self._lock:
            row = self._conn.execute(sql).fetchone()
        return dict(row) if row else None

    def get_history(self, field: str, hours: int = 24, limit: int = 1000) -> list[dict[str, Any]]:
        safe_fields = {
            "air_temp", "air_humi", "vpd_kpa", "ph", "soil_temp", "soil_humi", "ec", "lux", "eto_mm_day_est"
        }
        if field not in safe_fields:
            return []

        min_ts = int(time.time() * 1000) - (hours * 60 * 60 * 1000)
        sql = f"""
            SELECT timestamp_ms, {field} AS value, node, zone
            FROM samples
            WHERE timestamp_ms >= ? AND {field} IS NOT NULL
            ORDER BY timestamp_ms ASC
            LIMIT ?
        """
        with self._lock:
            rows = self._conn.execute(sql, (min_ts, limit)).fetchall()
        return [dict(r) for r in rows]

    def cleanup_old_data(self, retain_days: int) -> int:
        min_ts = int(time.time() * 1000) - (retain_days * 24 * 60 * 60 * 1000)
        sql = "DELETE FROM samples WHERE timestamp_ms < ?"
        with self._lock:
            with self._conn:
                cursor = self._conn.execute(sql, (min_ts,))
        return cursor.rowcount

    def get_scatter(self, xfield: str, yfield: str, hours: int = 24, limit: int = 1000) -> list[dict[str, Any]]:
        safe_fields = {"air_temp", "air_humi", "soil_temp", "soil_humi"}
        if xfield not in safe_fields or yfield not in safe_fields:
            return []

        min_ts = int(time.time() * 1000) - (hours * 60 * 60 * 1000)
        sql = f"""
            SELECT {xfield} AS x, {yfield} AS y, timestamp_ms, node, zone
            FROM samples
            WHERE timestamp_ms >= ?
              AND {xfield} IS NOT NULL
              AND {yfield} IS NOT NULL
            ORDER BY timestamp_ms ASC
            LIMIT ?
        """
        with self._lock:
            rows = self._conn.execute(sql, (min_ts, limit)).fetchall()
        return [dict(r) for r in rows]
