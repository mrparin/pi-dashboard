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

## ติดตั้งบน Raspberry Pi แบบละเอียด (Step by step)

คู่มือนี้เหมาะกับ Raspberry Pi OS (Bookworm/Bullseye) และทดสอบกับ Pi 3 ได้

## 1) เตรียมเครื่องครั้งแรก (ทำครั้งเดียว)

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git
```

ถ้าใช้ MQTT broker ภายนอก (เช่น `sci-iot.ddns.net`) ไม่จำเป็นต้องเปิด mosquitto ในเครื่องก็ได้

## 2) ดึงโปรเจกต์ลงเครื่อง Pi

กรณี clone ครั้งแรก:

```bash
cd /opt
sudo git clone <YOUR_REPO_URL> durian-dashboard
sudo chown -R pi:pi /opt/durian-dashboard
```

กรณีมีโฟลเดอร์เดิมอยู่แล้ว ให้ข้ามไปขั้นตอนอัปเดตเวอร์ชัน

## 3) อัปเดตเวอร์ชันใหม่จาก GitHub (แทนของเดิม)

```bash
cd /opt/durian-dashboard
git status
git pull origin main
```

ถ้า repository ใช้ branch `master` ให้เปลี่ยนคำสั่งเป็น:

```bash
git pull origin master
```

ถ้า `git pull` ติดเพราะมีไฟล์แก้ค้าง:

```bash
git stash
git pull origin main
git stash pop
```

## 4) ตั้งค่า `.env` ให้ตรงหน้างาน

สร้างไฟล์จากตัวอย่าง (ครั้งแรก):

```bash
cd /opt/durian-dashboard
cp .env.example .env
```

ตัวอย่างค่าที่ควรตรวจ:

```bash
MQTT_HOST=sci-iot.ddns.net
MQTT_PORT=1883
MQTT_TOPIC=durian_farm1/node_sensor
MQTT_QOS=1

DB_PATH=./data/durian_dashboard.db
RETAIN_DAYS=14

APP_HOST=0.0.0.0
APP_PORT=8080
REFRESH_SECONDS=3
```

หมายเหตุ:
- `RETAIN_DAYS` แนะนำ 7-14 วันสำหรับ Pi 3 เพื่อลดการเขียน SD card
- ถ้าใช้ broker ในเครื่องเดียวกัน ให้ใช้ `MQTT_HOST=127.0.0.1`

## 5) รันสคริปต์ติดตั้งอัตโนมัติ (แนะนำ)

สคริปต์อยู่ที่ `scripts/setup_pi_kiosk.sh` และจะทำครบทั้ง backend service + desktop autostart + browser autostart + screen timeout

ถ้าติดตั้งบน server อื่นและต้องการเฉพาะ backend service (ไม่เปิด browser อัตโนมัติ) ให้ใช้ `scripts/setup_pi_service_only.sh`

### แบบ service-only (ไม่เปิด browser อัตโนมัติ)

แบบถามคำถามก่อนติดตั้ง:

```bash
cd /opt/durian-dashboard
sudo bash scripts/setup_pi_service_only.sh
```

แบบไม่ถามคำถาม:

```bash
cd /opt/durian-dashboard
sudo bash scripts/setup_pi_service_only.sh --yes
```

สคริปต์นี้จะติดตั้งเฉพาะ:
- Python runtime dependencies และ virtual environment
- `durian-dashboard.service` ให้เริ่มอัตโนมัติหลังบูต
- ไม่แตะค่า desktop/autologin และไม่สร้าง browser autostart

### แบบถามคำถามก่อนติดตั้ง (interactive)

```bash
cd /opt/durian-dashboard
sudo bash scripts/setup_pi_kiosk.sh
```

ระบบจะถามค่า เช่น:
- Project directory
- Linux user (เช่น `pi`)
- Dashboard URL (ปกติใช้ `http://127.0.0.1:8080`)
- Screen timeout (วินาที) โดยค่าแนะนำคือ `3600`

### แบบไม่ถามคำถาม (non-interactive)

```bash
cd /opt/durian-dashboard
sudo bash scripts/setup_pi_kiosk.sh --yes
```

## 6) รีบูตและตรวจผลหลังติดตั้ง

```bash
sudo reboot
```

หลังเครื่องกลับมา:

```bash
sudo systemctl status durian-dashboard --no-pager
sudo ss -tulpn | grep 8080
```

สิ่งที่ต้องได้:
- service `durian-dashboard` เป็น `active (running)`
- Chromium เปิดหน้า dashboard อัตโนมัติแบบหน้าต่างปกติ (ไม่เต็มจอ)
- จอ idle 1 ชั่วโมงแล้วดับ และแตะจอแล้วติดกลับ

## 7) ทดสอบเร็ว 20 วินาที (ก่อนใช้งานจริง)

```bash
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority
xset s 20 0
xset +dpms
xset dpms 20 20 20
```

ทดสอบ:
- ปล่อยไว้ประมาณ 20 วินาที จอต้องดับ
- แตะหน้าจอ จอต้องติดกลับ

คืนค่าจริง 1 ชั่วโมง:

```bash
xset s 3600 0
xset +dpms
xset dpms 3600 3600 3600
```

## 8) คำสั่งตรวจสอบและแก้ปัญหาเบื้องต้น

ดู log แบบเรียลไทม์:

```bash
sudo journalctl -u durian-dashboard -f
```

รีสตาร์ต service หลังแก้ค่า:

```bash
sudo systemctl restart durian-dashboard
```

ถ้า Chromium ไม่เปิดอัตโนมัติ ให้ตรวจไฟล์เหล่านี้:
- `scripts/setup_pi_kiosk.sh`
- `/home/pi/start-dashboard-kiosk.sh`
- `/home/pi/.config/autostart/dashboard-kiosk.desktop`

## 9) อัปเดตโปรเจกต์รอบถัดไป

ทุกครั้งที่มี release ใหม่จาก GitHub:

```bash
cd /opt/durian-dashboard
git pull origin main
sudo bash scripts/setup_pi_kiosk.sh --yes
sudo systemctl restart durian-dashboard
```

## Environment variables (reference)

ค่าที่รองรับในระบบ:

```bash
MQTT_HOST
MQTT_PORT
MQTT_TOPIC
MQTT_QOS
DB_PATH
RETAIN_DAYS
APP_HOST
APP_PORT
REFRESH_SECONDS
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

## Notes for Pi3

- Keep retention low (7-14 days) to protect SD card.
- Use one Uvicorn worker.
- Keep MQTT publish interval at 1-5 minutes.
