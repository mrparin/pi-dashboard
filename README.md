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

### ติดตั้งแบบคำสั่งเดียว (แนะนำสำหรับงานติดตั้งหน้างาน)

ถ้าต้องการให้เครื่องบูตแล้วเปิด Dashboard อัตโนมัติแบบ Kiosk (Chromium) พร้อมตั้งจอดับเมื่อไม่มีการแตะ 1 ชั่วโมง ให้ใช้สคริปต์นี้:

```bash
cd /opt/durian-dashboard
sudo bash scripts/setup_pi_kiosk.sh
```

เมื่อรันคำสั่งนี้ ระบบจะถามค่าก่อนเริ่มติดตั้ง (interactive) เช่น user, URL และเวลา timeout ของจอ

ถ้าต้องการรันแบบไม่ถามคำถาม ให้ใช้:

```bash
cd /opt/durian-dashboard
sudo bash scripts/setup_pi_kiosk.sh --yes
```

สคริปต์จะทำงานให้ครบดังนี้:
- ติดตั้งแพ็กเกจที่จำเป็น (`python3-venv`, `python3-pip`, `curl`, `unclutter`, `chromium`)
- สร้าง/อัปเดต `.venv` และติดตั้ง dependencies จาก `requirements.txt`
- ติดตั้งและเปิดใช้งาน `durian-dashboard.service` ให้เริ่มอัตโนมัติหลังบูต
- ตั้ง Desktop Autologin (ถ้า `raspi-config` รองรับ non-interactive)
- สร้าง Kiosk launcher และ autostart ให้เปิด Chromium หน้า Dashboard อัตโนมัติ
- ตั้ง timeout จอเป็น 1 ชั่วโมง (`3600` วินาที) และแตะจอเพื่อปลุกได้

เสร็จแล้วรีบูต:

```bash
sudo reboot
```

### 1) เตรียมระบบปฏิบัติการ

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3-venv python3-pip mosquitto mosquitto-clients
```

ถ้าใช้ MQTT broker ภายนอก (เช่น `sci-iot.ddns.net`) ไม่จำเป็นต้องเปิด mosquitto ในเครื่องก็ได้

### 2) วางโปรเจกต์ลงในเครื่อง Pi

กรณีมี Git repository:

```bash
cd /opt
sudo git clone <YOUR_REPO_URL> durian-dashboard
sudo chown -R pi:pi /opt/durian-dashboard
```

กรณีไม่มี Git: คัดลอกโฟลเดอร์โปรเจกต์ไปที่ `/opt/durian-dashboard` แล้วตั้งสิทธิ์ให้ user `pi`

### 3) สร้าง virtual environment และติดตั้ง dependencies

```bash
cd /opt/durian-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) ตั้งค่า environment ของระบบ

สร้างไฟล์ `.env` จากตัวอย่าง:

```bash
cd /opt/durian-dashboard
cp .env.example .env
```

แก้ไฟล์ `.env` ให้ตรงกับหน้างาน:

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
- ถ้าใช้ broker ในเครื่องเดียวกัน ให้เปลี่ยน `MQTT_HOST=127.0.0.1`

### 5) ทดสอบรันแบบ manual ก่อน

```bash
cd /opt/durian-dashboard
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1
```

เปิดจากเครื่องอื่นในเครือข่ายเดียวกัน:

```text
http://<PI_IP>:8080
```

ถ้า MQTT ยังไม่มา หน้าเว็บจะเปิดได้ปกติ แต่ข้อมูล card/chart จะยังว่างจนกว่าจะมี message เข้า topic

### 6) ตั้งให้รันอัตโนมัติด้วย systemd

โปรเจกต์มีไฟล์ service ให้แล้วที่ `systemd/durian-dashboard.service`

คัดลอก service ไปที่ระบบ:

```bash
sudo cp /opt/durian-dashboard/systemd/durian-dashboard.service /etc/systemd/system/durian-dashboard.service
```

ตรวจค่าใน service ให้ตรงเครื่องจริง (สำคัญ):
- `User=pi`
- `Group=pi`
- `WorkingDirectory=/opt/durian-dashboard`
- `ExecStart=/opt/durian-dashboard/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1`

เปิดใช้งาน service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable durian-dashboard
sudo systemctl start durian-dashboard
sudo systemctl status durian-dashboard
```

### 7) คำสั่งตรวจสอบและแก้ปัญหาเบื้องต้น

ดู log แบบเรียลไทม์:

```bash
sudo journalctl -u durian-dashboard -f
```

รีสตาร์ต service หลังแก้ค่า:

```bash
sudo systemctl restart durian-dashboard
```

ตรวจพอร์ต 8080:

```bash
sudo ss -tulpn | grep 8080
```

### 8) การอัปเดตโปรเจกต์ในอนาคต

```bash
cd /opt/durian-dashboard
git pull
source .venv/bin/activate
pip install -r requirements.txt
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
