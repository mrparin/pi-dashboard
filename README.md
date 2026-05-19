# Durian Dashboard (Python Native)

Lightweight MQTT dashboard for Raspberry Pi 3 without Node-RED, InfluxDB, or ThingsBoard.

## Stack

- FastAPI (web app + API + websocket)
- paho-mqtt (MQTT subscriber)
- SQLite (short-term history)
- Jinja2 + Chart.js (dashboard UI)

## Features

- Subscribes to `durian_farm1/node_sensor`
- Normalizes payload fields (`air_temp`/`Air_temp`, `soil_temp`/`Soil_temp`)
- Calculates derived metrics:
  - `es_kpa`, `ea_kpa`, `vpd_kpa`
  - `solar_wm2_est`, `solar_mj_m2_h_est`
  - `eto_mm_h_est`, `eto_mm_day_est`
- Computes status and recommendation fields:
  - `vpd_status`, `vpd_message`, `vpd_action`
  - `ph_status`, `ph_message`, `ph_action`
- Realtime cards and history charts (24h / 7d)

## Install (native)

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip mosquitto mosquitto-clients

cd /opt/durian-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Open: `http://<pi-ip>:8080`

The web app can start even if MQTT is not available yet. In that case the dashboard loads normally, but cards and charts stay empty until messages arrive on the configured topic.

## Environment variables

```bash
export MQTT_HOST=127.0.0.1
export MQTT_PORT=1883
export MQTT_TOPIC=durian_farm1/node_sensor
export MQTT_QOS=1

export DB_PATH=./data/durian_dashboard.db
export RETAIN_DAYS=14

export APP_HOST=0.0.0.0
export APP_PORT=8080
export REFRESH_SECONDS=3
```

## API

- `GET /api/latest`
- `GET /api/history?field=vpd_kpa&hours=24`
- `WS /ws`

## Payload example

```json
{
  "time": "19/05/2026 09:30:00",
  "node": "node01",
  "zone": "zone01",
  "env": {
    "air_temp": 30.5,
    "air_humi": 72.0,
    "lux": 54000,
    "wind_speed_avg5m": 1.2,
    "wind_dir_deg": 135,
    "wind_dir_th": "SE"
  },
  "npk": {
    "soil_temp": 28.4,
    "soil_humi": 65.0,
    "ec": 1.25,
    "ph": 6.4,
    "n": 45,
    "p": 18,
    "k": 120
  }
}
```

## Production service (systemd)

Copy `systemd/durian-dashboard.service` to `/etc/systemd/system/durian-dashboard.service` and adjust `WorkingDirectory`/`User`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable durian-dashboard
sudo systemctl start durian-dashboard
sudo systemctl status durian-dashboard
```

## Notes for Pi3

- Keep retention low (7-14 days) to protect SD card.
- Use one Uvicorn worker.
- Keep MQTT publish interval at 1-5 minutes.
