from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.db import Database
from app.mqtt_client import MqttIngestClient
from app.service import DataService

from typing import Literal

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
