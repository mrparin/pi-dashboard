from __future__ import annotations

import datetime as dt
import math
from typing import Any
from zoneinfo import ZoneInfo

from app.config import Settings


def parse_sensor_time(raw: Any, timezone_name: str = "Asia/Bangkok") -> int:
    if isinstance(raw, str):
        try:
            parsed = dt.datetime.strptime(raw, "%d/%m/%Y %H:%M:%S")
            parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
            return int(parsed.timestamp() * 1000)
        except ValueError:
            pass
    return int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)


def saturation_vapor_pressure_kpa(air_temp_c: float) -> float:
    return 0.6108 * math.exp((17.27 * air_temp_c) / (air_temp_c + 237.3))


def calc_vpd(air_temp_c: float, air_humi_pct: float) -> tuple[float, float, float]:
    es_kpa = saturation_vapor_pressure_kpa(air_temp_c)
    ea_kpa = es_kpa * (air_humi_pct / 100.0)
    return es_kpa, ea_kpa, es_kpa - ea_kpa


def calc_solar(lux: float, lux_per_wm2: float = 120.0) -> tuple[float, float]:
    if lux_per_wm2 <= 0:
        raise ValueError("lux_per_wm2 must be greater than zero")
    solar_wm2 = max(0.0, lux) / lux_per_wm2
    solar_mj_m2_h = solar_wm2 * 3600.0 / 1_000_000.0
    return solar_wm2, solar_mj_m2_h


def atmospheric_pressure_kpa(altitude_m: float) -> float:
    return 101.3 * (((293.0 - (0.0065 * altitude_m)) / 293.0) ** 5.26)


def psychrometric_constant_kpa_c(altitude_m: float) -> float:
    return 0.000665 * atmospheric_pressure_kpa(altitude_m)


def wind_speed_at_2m(wind_speed_ms: float, measurement_height_m: float) -> float:
    """FAO-56 equation 47: normalize wind measured at z metres to 2 metres."""
    speed = max(0.0, wind_speed_ms)
    if math.isclose(measurement_height_m, 2.0):
        return speed
    if measurement_height_m <= 0.1:
        raise ValueError("wind measurement height must be greater than 0.1 m")
    return speed * 4.87 / math.log((67.8 * measurement_height_m) - 5.42)


def calc_fao56_hourly_eto(
    air_temp_c: float,
    vpd_kpa: float,
    wind_speed_ms: float,
    net_radiation_mj_m2_h: float,
    soil_heat_flux_mj_m2_h: float,
    altitude_m: float = 0.0,
) -> float:
    """FAO-56 equation 53, returning reference ET in mm/hour."""
    gamma = psychrometric_constant_kpa_c(altitude_m)
    delta = (4098.0 * saturation_vapor_pressure_kpa(air_temp_c)) / ((air_temp_c + 237.3) ** 2)
    u2 = max(0.0, wind_speed_ms)
    available_energy = net_radiation_mj_m2_h - soil_heat_flux_mj_m2_h
    numerator = (0.408 * delta * available_energy) + (
        gamma * (37.0 / (air_temp_c + 273.0)) * u2 * max(0.0, vpd_kpa)
    )
    denominator = delta + gamma * (1.0 + 0.34 * u2)
    return max(0.0, numerator / denominator) if denominator else 0.0


def hourly_extraterrestrial_radiation(
    local_time: dt.datetime,
    latitude_deg: float,
    longitude_deg: float,
) -> float:
    """FAO-56 equation 28, MJ m-2 hour-1, for a one-hour period."""
    if local_time.tzinfo is None:
        raise ValueError("local_time must be timezone-aware")

    day = local_time.timetuple().tm_yday
    latitude = math.radians(latitude_deg)
    dr = 1.0 + 0.033 * math.cos((2.0 * math.pi / 365.0) * day)
    declination = 0.409 * math.sin(((2.0 * math.pi / 365.0) * day) - 1.39)
    sunset_angle = math.acos(max(-1.0, min(1.0, -math.tan(latitude) * math.tan(declination))))

    utc_offset_h = (local_time.utcoffset() or dt.timedelta()).total_seconds() / 3600.0
    standard_meridian = 15.0 * utc_offset_h
    b = (2.0 * math.pi * (day - 81)) / 364.0
    seasonal_correction_h = (
        0.1645 * math.sin(2.0 * b)
        - 0.1255 * math.cos(b)
        - 0.025 * math.sin(b)
    )
    clock_hour = local_time.hour + local_time.minute / 60.0 + local_time.second / 3600.0
    solar_hour = clock_hour + (0.06667 * (longitude_deg - standard_meridian)) + seasonal_correction_h
    midpoint_angle = (math.pi / 12.0) * (solar_hour - 12.0)
    half_hour_angle = math.pi / 24.0
    omega1 = max(-sunset_angle, midpoint_angle - half_hour_angle)
    omega2 = min(sunset_angle, midpoint_angle + half_hour_angle)
    if omega2 <= omega1:
        return 0.0

    gsc = 0.0820
    ra = ((12.0 * 60.0) / math.pi) * gsc * dr * (
        ((omega2 - omega1) * math.sin(latitude) * math.sin(declination))
        + (math.cos(latitude) * math.cos(declination) * (math.sin(omega2) - math.sin(omega1)))
    )
    return max(0.0, ra)


def calc_hourly_net_radiation(
    air_temp_c: float,
    actual_vapor_pressure_kpa: float,
    solar_radiation_mj_m2_h: float,
    extraterrestrial_radiation_mj_m2_h: float,
    altitude_m: float,
) -> tuple[float, float]:
    """FAO-56 equations 37-40 and 45-46; returns (Rn, G)."""
    rs = max(0.0, solar_radiation_mj_m2_h)
    ra = max(0.0, extraterrestrial_radiation_mj_m2_h)
    rso = (0.75 + (2e-5 * altitude_m)) * ra
    rns = 0.77 * rs

    if rso > 0:
        cloud_ratio = max(0.3, min(1.0, rs / rso))
    else:
        # FAO-56 suggests 0.4-0.6 at night in humid/sub-humid climates.
        cloud_ratio = 0.5
    sigma_hourly = 2.043e-10
    temperature_k = air_temp_c + 273.16
    humidity_term = max(0.0, 0.34 - (0.14 * math.sqrt(max(0.0, actual_vapor_pressure_kpa))))
    cloud_term = (1.35 * cloud_ratio) - 0.35
    rnl = sigma_hourly * (temperature_k**4) * humidity_term * cloud_term
    rn = rns - rnl
    soil_heat_flux = (0.1 if ra > 0 else 0.5) * rn
    return rn, soil_heat_flux


def get_vpd_status(vpd: float) -> dict[str, str]:
    if vpd < 0.40:
        return {
            "level": "too_low",
            "text": "VPD ต่ำเกินไป: อากาศชื้นจัด เสี่ยงโรครา",
            "action": "งดให้น้ำ/งดพ่นหมอก และเพิ่มการระบายอากาศ",
            "color": "blue",
        }
    if vpd <= 0.80:
        return {
            "level": "low_stress",
            "text": "VPD ค่อนข้างต่ำ: เฝ้าระวังความชื้นสูง",
            "action": "ระบบทำงานปกติ ไม่ต้องเปิดพ่นหมอกเพิ่ม",
            "color": "green",
        }
    if vpd <= 1.40:
        return {
            "level": "optimal",
            "text": "VPD เหมาะสมที่สุดสำหรับทุเรียน",
            "action": "รักษาระดับนี้ไว้",
            "color": "teal",
        }
    if vpd <= 1.80:
        return {
            "level": "high_stress",
            "text": "VPD เริ่มวิกฤต: อากาศแห้งและร้อน",
            "action": "ควรเปิดระบบพ่นหมอกเพื่อเพิ่มความชื้น",
            "color": "amber",
        }
    return {
        "level": "danger",
        "text": "VPD วิกฤตรุนแรง: เสี่ยงใบไหม้และผลร่วง",
        "action": "เปิดระบบพ่นหมอกเต็มกำลัง และเพิ่มรอบให้น้ำโคนต้น",
        "color": "red",
    }


def get_ph_status(ph: float) -> dict[str, str]:
    if ph < 5.0:
        return {
            "level": "strong_acid",
            "text": "ดินเป็นกรดรุนแรง",
            "action": "ตรวจสอบซ้ำและพิจารณาปรับปรุงดิน",
            "color": "red",
        }
    if ph <= 5.5:
        return {
            "level": "acid",
            "text": "ดินเป็นกรด",
            "action": "เฝ้าระวังและตรวจร่วมกับ EC/NPK",
            "color": "orange",
        }
    if ph <= 6.5:
        return {
            "level": "suitable",
            "text": "pH อยู่ในช่วงเหมาะสม",
            "action": "รักษาสภาพดินและติดตามต่อเนื่อง",
            "color": "teal",
        }
    if ph <= 7.5:
        return {
            "level": "near_neutral",
            "text": "ดินใกล้กลาง",
            "action": "ติดตามร่วมกับ EC และธาตุอาหาร",
            "color": "amber",
        }
    return {
        "level": "alkaline",
        "text": "ดินเป็นด่าง",
        "action": "ตรวจสอบสภาพดินและความพร้อมใช้ของธาตุอาหาร",
        "color": "blue",
    }


def normalize_payload(payload: dict[str, Any], settings: Settings | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("MQTT payload must be a JSON object")
    settings = settings or Settings()
    env = payload.get("env", {}) or {}
    npk = payload.get("npk", {}) or {}

    air_temp = env.get("air_temp", env.get("Air_temp"))
    air_humi = env.get("air_humi", env.get("Air_humi"))
    soil_temp = npk.get("soil_temp", npk.get("Soil_temp"))
    soil_humi = npk.get("soil_humi", npk.get("Soil_humi"))

    record: dict[str, Any] = {
        "timestamp_ms": parse_sensor_time(payload.get("time"), settings.station_timezone),
        "node": payload.get("node", "unknown_node"),
        "zone": payload.get("zone", "unknown_zone"),
        "air_temp": air_temp,
        "air_humi": air_humi,
        "lux": env.get("lux"),
        "wind_speed_avg5m": env.get("wind_speed_avg5m"),
        "wind_dir_deg": env.get("wind_dir_deg"),
        "wind_dir_th": env.get("wind_dir_th"),
        "soil_temp": soil_temp,
        "soil_humi": soil_humi,
        "ec": npk.get("ec"),
        "ph": npk.get("ph"),
        "n": npk.get("n"),
        "p": npk.get("p"),
        "k": npk.get("k"),
    }

    if isinstance(air_temp, (int, float)) and isinstance(air_humi, (int, float)):
        es_kpa, ea_kpa, vpd_kpa = calc_vpd(float(air_temp), float(air_humi))
        record["es_kpa"] = es_kpa
        record["ea_kpa"] = ea_kpa
        record["vpd_kpa"] = vpd_kpa
        record.update({
            "vpd_status": get_vpd_status(vpd_kpa)["level"],
            "vpd_message": get_vpd_status(vpd_kpa)["text"],
            "vpd_action": get_vpd_status(vpd_kpa)["action"],
        })

    if isinstance(record.get("lux"), (int, float)):
        solar_wm2, solar_mj_m2_h = calc_solar(float(record["lux"]), settings.lux_per_wm2)
        record["solar_wm2_est"] = solar_wm2
        record["solar_mj_m2_h_est"] = solar_mj_m2_h

    if (
        isinstance(record.get("air_temp"), (int, float))
        and isinstance(record.get("vpd_kpa"), (int, float))
        and isinstance(record.get("solar_mj_m2_h_est"), (int, float))
        and settings.station_latitude is not None
        and settings.station_longitude is not None
    ):
        wind = record.get("wind_speed_avg5m") if isinstance(record.get("wind_speed_avg5m"), (int, float)) else 0.0
        local_time = dt.datetime.fromtimestamp(
            record["timestamp_ms"] / 1000.0, ZoneInfo(settings.station_timezone)
        )
        ra = hourly_extraterrestrial_radiation(
            local_time,
            settings.station_latitude,
            settings.station_longitude,
        )
        rn, soil_heat_flux = calc_hourly_net_radiation(
            float(record["air_temp"]),
            float(record["ea_kpa"]),
            float(record["solar_mj_m2_h_est"]),
            ra,
            settings.station_altitude_m,
        )
        u2 = wind_speed_at_2m(float(wind), settings.wind_sensor_height_m)
        record["eto_mm_h_est"] = calc_fao56_hourly_eto(
            float(record["air_temp"]),
            float(record["vpd_kpa"]),
            u2,
            rn,
            soil_heat_flux,
            settings.station_altitude_m,
        )

    if isinstance(record.get("ph"), (int, float)):
        ph_status = get_ph_status(float(record["ph"]))
        record["ph_status"] = ph_status["level"]
        record["ph_message"] = ph_status["text"]
        record["ph_action"] = ph_status["action"]

    return record
