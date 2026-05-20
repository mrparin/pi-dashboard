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

## คู่มือการติดตั้งและอัปเดต

### 1) การติดตั้งลงใน Raspberry Pi

เหมาะกับ Raspberry Pi OS (Bookworm/Bullseye) และทดสอบกับ Pi 3

เตรียมเครื่องครั้งแรก:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git
```

ดึงโปรเจกต์ครั้งแรก:

```bash
cd /opt
sudo git clone <YOUR_REPO_URL> durian-dashboard
sudo chown -R pi:pi /opt/durian-dashboard
```

ตั้งค่าไฟล์ `.env` (ครั้งแรก):

```bash
cd /opt/durian-dashboard
cp .env.example .env
```

ติดตั้งแบบ kiosk (เปิด browser อัตโนมัติ):

```bash
cd /opt/durian-dashboard
sudo bash scripts/setup_pi_kiosk.sh --yes
```

ตรวจผลหลังติดตั้ง:

```bash
sudo systemctl status durian-dashboard --no-pager
sudo ss -tulpn | grep 8080
```

ปิดหน้า browser/kiosk ปัจจุบัน (กรณีต้องการหยุดชั่วคราว):

```bash
pkill -f start-dashboard-kiosk.sh
pkill -f "chromium|chromium-browser"
```

หมายเหตุ:
- ถ้าหน้างานไม่ได้ใช้ broker ในเครื่องเดียวกัน ให้ตั้ง `MQTT_HOST` เป็น broker ปลายทาง
- ถ้าเก็บข้อมูลจริงไว้ที่ server อยู่แล้ว แนะนำตั้ง `RETAIN_DAYS=90` (เก็บ local cache 3 เดือน)

### 2) การ update software จาก git ใหม่

ใช้เมื่อมีการเปลี่ยนแปลงซอฟต์แวร์ใหม่ใน repository

```bash
cd /opt/durian-dashboard
git status
git pull origin main
```

ถ้าโครงการใช้ branch `master`:

```bash
git pull origin master
```

ถ้า pull ไม่ได้เพราะมีไฟล์แก้ค้าง:

```bash
git stash
git pull origin main
git stash pop
```

อัปเดต dependency/service หลัง pull:

```bash
sudo bash scripts/setup_pi_kiosk.sh --yes
sudo systemctl restart durian-dashboard
```

### 3) ติดตั้งไปยังเครื่อง server ใหม่ (user ไม่เหมือน Raspberry Pi)

กรณีเครื่องใหม่มี user ไม่ใช่ `pi` (ตัวอย่างใช้ `bigdata`):

```bash
cd /opt/durian-dashboard
sudo PI_USER=bigdata APP_DIR=/opt/durian-dashboard bash scripts/setup_pi_service_only.sh --yes
```

ตรวจว่า service ถูก deploy ด้วย user/group ที่ถูกต้อง:

```bash
sudo systemctl cat durian-dashboard | grep -E '^(User|Group)='
```

ตัวอย่างผลที่ควรได้:

```bash
User=bigdata
Group=bigdata
```

ถ้าพอร์ต 8080 ถูกใช้งานอยู่แล้ว ให้เปลี่ยนพอร์ตในไฟล์ service แล้ว reload:

```bash
sudo sed -i 's/--port 8080/--port 8081/' /etc/systemd/system/durian-dashboard.service
sudo systemctl daemon-reload
sudo systemctl restart durian-dashboard
```

### 4) การติดตั้งเฉพาะ service อย่างเดียว (ไม่เปิด browser อัตโนมัติ)

ใช้สคริปต์ `scripts/setup_pi_service_only.sh`

แบบ interactive:

```bash
cd /opt/durian-dashboard
sudo bash scripts/setup_pi_service_only.sh
```

แบบ non-interactive:

```bash
cd /opt/durian-dashboard
sudo bash scripts/setup_pi_service_only.sh --yes
```

สิ่งที่สคริปต์นี้ทำ:
- ติดตั้ง Python packages ที่จำเป็น
- สร้าง/อัปเดต virtual environment
- ติดตั้งและเริ่ม `durian-dashboard.service`

สิ่งที่สคริปต์นี้ไม่ทำ:
- ไม่ตั้งค่า desktop autologin
- ไม่สร้าง browser autostart

ตรวจสถานะหลังติดตั้ง:

```bash
sudo systemctl status durian-dashboard --no-pager
sudo journalctl -u durian-dashboard -n 100 --no-pager
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

### Data retention policy (local cache)

- ค่าแนะนำสำหรับหน้างานที่มีข้อมูลหลักอยู่บน server: `RETAIN_DAYS=90`
- ระบบจะลบข้อมูลที่เก่ากว่า `RETAIN_DAYS` อัตโนมัติระหว่างรัน (ตรวจทุก ~1 ชั่วโมง)
- สามารถปรับในไฟล์ `.env` ได้ตามต้องการ

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


## Next steps (Post-install verification)

1. Reboot the device:
  ```bash
  sudo reboot
  ```
2. After boot, verify the service is running:
  ```bash
  sudo systemctl status durian-dashboard --no-pager
  ```
3. Verify the web port is open:
  ```bash
  sudo ss -tulpn | grep 8080
  ```

### Optional: Quick screen timeout test (20 seconds)

```bash
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority
xset s 20 0
xset +dpms
xset dpms 20 20 20
```

### Restore 1-hour screen timeout

```bash
xset s 3600 0
xset +dpms
xset dpms 3600 3600 3600
```

## Notes for Pi3

- If upstream server stores long-term data, keep local cache at `RETAIN_DAYS=90`.
- Use one Uvicorn worker.
- Keep MQTT publish interval at 1-5 minutes.
