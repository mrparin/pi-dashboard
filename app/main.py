from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Literal

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.db import Database
from app.mqtt_client import MqttIngestClient
from app.service import DataService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


db = Database(settings.db_path)
service = DataService(db)
mqtt_client = MqttIngestClient(settings, service)


async def periodic_cleanup(stop_event: asyncio.Event) -> None:
    # Run periodic retention cleanup so DB size stays bounded even without restarts.
    while not stop_event.is_set():
        try:
            deleted = db.cleanup_old_data(settings.retain_days)
            if deleted:
                logger.info("Periodic cleanup removed %s rows", deleted)
        except Exception as exc:  # pragma: no cover
            logger.exception("Periodic cleanup failed: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=3600)
        except asyncio.TimeoutError:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    cleanup_task = asyncio.create_task(periodic_cleanup(stop_event))
    mqtt_client.start()
    logger.info("Application startup complete")
    try:
        yield
    finally:
        stop_event.set()
        await cleanup_task
        mqtt_client.stop()
        deleted = db.cleanup_old_data(settings.retain_days)
        logger.info("Cleanup removed %s rows", deleted)
        db.close()
        logger.info("Application shutdown complete")


app = FastAPI(title="Durian Dashboard", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "refresh_seconds": settings.refresh_seconds,
            "topic": settings.mqtt_topic,
        },
    )


@app.get("/api/latest")
async def api_latest() -> JSONResponse:
    latest = service.get_latest()
    return JSONResponse(content={"data": latest})


@app.get("/api/history")
async def api_history(
    field: str = Query("vpd_kpa"),
    hours: int = Query(24, ge=1, le=168),
) -> JSONResponse:
    rows = service.get_history(field=field, hours=hours)
    return JSONResponse(content={"field": field, "hours": hours, "points": rows})


# --- New: API for scatter plot pairs ---
@app.get("/api/scatter")
async def api_scatter(
    pair: Literal["air", "soil"] = Query("air"),
    hours: int = Query(24, ge=1, le=168),
) -> JSONResponse:
    # Get (x, y) pairs for scatter plot
    if pair == "air":
        xfield, yfield = "air_temp", "air_humi"
    else:
        xfield, yfield = "soil_temp", "soil_humi"
    points = service.get_scatter(xfield, yfield, hours=hours)
    return JSONResponse(content={"pair": pair, "hours": hours, "points": points})


@app.get("/api/geocode")
async def api_geocode(q: str = Query(..., min_length=1, max_length=100)) -> JSONResponse:
    """Proxy Open-Meteo geocoding API – returns matching places for a given name."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": q, "count": 8, "language": "th"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Geocoding service unavailable: {exc}")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Geocoding service error: {exc.response.status_code}")

    results = [
        {
            "name": r.get("name", ""),
            "admin1": r.get("admin1", ""),
            "lat": r.get("latitude"),
            "lon": r.get("longitude"),
        }
        for r in data.get("results", [])
    ]
    return JSONResponse(content={"results": results})


TMD_CONDITIONS: dict[int, tuple[str, int]] = {
    1: ("ท้องฟ้าแจ่มใส", 0),
    2: ("มีเมฆบางส่วน", 2),
    3: ("เมฆเป็นส่วนมาก", 3),
    4: ("มีเมฆมาก", 3),
    5: ("ฝนเล็กน้อย", 61),
    6: ("ฝนปานกลาง", 63),
    7: ("ฝนตกหนัก", 65),
    8: ("ฝนฟ้าคะนอง", 95),
    9: ("อากาศหนาวจัด", 3),
    10: ("อากาศหนาว", 3),
    11: ("อากาศเย็น", 3),
    12: ("อากาศร้อนจัด", 0),
}


def normalize_tmd_forecast(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert the TMD NWP response to the daily shape consumed by the UI."""
    groups = payload.get("WeatherForecasts")
    if not isinstance(groups, list) or not groups:
        raise ValueError("TMD response has no WeatherForecasts")

    group = groups[0]
    forecasts = group.get("forecasts")
    if not isinstance(forecasts, list) or not forecasts:
        raise ValueError("TMD response has no forecasts")

    days = forecasts[:7]
    weather_codes: list[int] = []
    condition_text: list[str] = []
    for item in days:
        condition = int(item.get("data", {}).get("cond") or 0)
        text, wmo_code = TMD_CONDITIONS.get(condition, ("ไม่ทราบสภาพอากาศ", 3))
        condition_text.append(text)
        weather_codes.append(wmo_code)

    return {
        "source": "tmd",
        "source_label": "กรมอุตุนิยมวิทยา (TMD)",
        "location": group.get("location"),
        "daily_units": {
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
            "precipitation_sum": "mm",
            "precipitation_probability_max": "%",
            "windspeed_10m_max": "km/h",
        },
        "daily": {
            "time": [item.get("time", "").split("T", 1)[0] for item in days],
            "weathercode": weather_codes,
            "condition_text": condition_text,
            "temperature_2m_max": [item.get("data", {}).get("tc_max") for item in days],
            "temperature_2m_min": [item.get("data", {}).get("tc_min") for item in days],
            "precipitation_sum": [item.get("data", {}).get("rain") for item in days],
            "precipitation_probability_max": [None for _ in days],
            # TMD ws10m is m/s; the existing card displays km/h.
            "windspeed_10m_max": [
                round(float(item.get("data", {}).get("ws10m")) * 3.6, 1)
                if item.get("data", {}).get("ws10m") is not None
                else None
                for item in days
            ],
        },
    }


async def fetch_tmd_forecast(client: httpx.AsyncClient, lat: float, lon: float) -> dict[str, Any]:
    response = await client.get(
        "https://data.tmd.go.th/nwpapi/v1/forecast/location/daily/at",
        params={
            "lat": lat,
            "lon": lon,
            "fields": "tc_max,tc_min,rain,cond,ws10m,rh",
            "duration": 7,
        },
        headers={
            "Authorization": f"Bearer {settings.tmd_access_token}",
            "Accept": "application/json",
        },
    )
    response.raise_for_status()
    return normalize_tmd_forecast(response.json())


async def fetch_open_meteo_forecast(
    client: httpx.AsyncClient,
    lat: float,
    lon: float,
    fallback_reason: str,
) -> dict[str, Any]:
    response = await client.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": (
                "weathercode,temperature_2m_max,temperature_2m_min,"
                "precipitation_sum,precipitation_probability_max,windspeed_10m_max"
            ),
            "timezone": "Asia/Bangkok",
            "forecast_days": 7,
        },
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("daily", {}).get("time"):
        raise ValueError("Open-Meteo response has no daily forecast")
    data.update(
        {
            "source": "open_meteo",
            "source_label": "Open-Meteo (ข้อมูลสำรอง)",
            "fallback_reason": fallback_reason,
        }
    )
    return data


async def add_rain_probability(
    forecast: dict[str, Any],
    client: httpx.AsyncClient,
    lat: float,
    lon: float,
) -> None:
    """Populate rain probability when the primary forecast provider omits it."""
    probability_forecast = await fetch_open_meteo_forecast(
        client, lat, lon, "rain_probability"
    )
    forecast["daily"]["precipitation_probability_max"] = probability_forecast[
        "daily"
    ]["precipitation_probability_max"]
    forecast["rain_probability_source"] = "open_meteo"


@app.get("/api/weather")
async def api_weather(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> JSONResponse:
    """Return TMD daily forecast, falling back to Open-Meteo when necessary."""
    fallback_reason = "tmd_token_missing"
    async with httpx.AsyncClient(timeout=10) as client:
        if settings.tmd_access_token:
            try:
                forecast = await fetch_tmd_forecast(client, lat, lon)
                try:
                    await add_rain_probability(forecast, client, lat, lon)
                except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
                    logger.warning("Rain probability unavailable from Open-Meteo: %s", exc)
                return JSONResponse(content=forecast)
            except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
                fallback_reason = "tmd_unavailable"
                logger.warning("TMD forecast unavailable; using Open-Meteo fallback: %s", exc)
        else:
            logger.warning("TMD_ACCESS_TOKEN is not configured; using Open-Meteo fallback")

        try:
            fallback = await fetch_open_meteo_forecast(client, lat, lon, fallback_reason)
            return JSONResponse(content=fallback)
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            logger.error("Both weather providers are unavailable: %s", exc)
            raise HTTPException(status_code=502, detail="Weather providers are unavailable") from exc


@app.websocket("/ws")
async def websocket_latest(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            latest = service.get_latest()
            await websocket.send_text(json.dumps({"data": latest}))
            await asyncio.sleep(max(1, settings.refresh_seconds))
    except WebSocketDisconnect:
        return
