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
  - `eto_mm_h_est` using the FAO-56 hourly Penman-Monteith equation
  - `eto_mm_day_est` as the observed local-day integral of the hourly rate
- Computes status and recommendation fields:
  - `vpd_status`, `vpd_message`, `vpd_action`
  - `ph_status`, `ph_message`, `ph_action`
- Realtime cards and history charts (24h / 7d)

## การรันบนเครื่อง local (Windows) เพื่อทดสอบ

ใช้ขั้นตอนนี้เพื่อทดสอบโปรเจกต์บนเครื่องนี้ (path ปัจจุบัน: `D:\codeArduino\vscode\pi-dashboard`)

### แบบใช้ Command Prompt (cmd)

1) เข้าโฟลเดอร์โปรเจกต์

```bat
cd /d D:\codeArduino\vscode\pi-dashboard
```

2) สร้าง virtual environment (ครั้งแรกเท่านั้น)

```bat
py -3 -m venv .venv
```

3) activate environment

```bat
.venv\Scripts\activate
```

4) ติดตั้ง dependencies

```bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

5) รันแอปเพื่อทดสอบ

```bat
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

6) เปิดหน้าเว็บทดสอบ

- Dashboard: http://127.0.0.1:8080
- Latest API: http://127.0.0.1:8080/api/latest

7) หยุดแอป

กด `Ctrl + C` ในหน้าต่าง cmd ที่กำลังรัน Uvicorn

### แบบใช้ PowerShell

```powershell
cd D:\codeArduino\vscode\pi-dashboard
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

หมายเหตุ:
- ถ้าระบบบล็อกการรันสคริปต์ตอน activate บน PowerShell ให้รันคำสั่งนี้ครั้งเดียวก่อน:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

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

### 2) การ deploy โค้ดเวอร์ชันใหม่จาก Git เข้า server

ขั้นตอนนี้ใช้กับ server ที่ติดตั้งโปรเจกต์ไว้ที่ `/opt/durian-dashboard` และรันผ่าน
`durian-dashboard.service` ตัวอย่างใช้ branch `02_addweather` และ user/group `bigdata`
ให้ปรับชื่อ branch, user, path และ port ให้ตรงกับเครื่องจริง

> **สำคัญ:** `data/durian_dashboard.db` เป็นฐานข้อมูล runtime ที่ service เขียนอยู่ตลอด
> ห้าม `git pull`, `git stash`, `git reset --hard` หรือคัดลอกทับฐานข้อมูลขณะที่ service ยังทำงาน
> ต้องหยุด service และสำรองฐานข้อมูลไว้นอก repository ก่อนทุกครั้ง

#### 2.1 ตรวจสอบ service และ Git ก่อน deploy

```bash
sudo systemctl cat durian-dashboard --no-pager
cd /opt/durian-dashboard
git status --short --branch
git branch --show-current
```

ดึงข้อมูล remote โดยยังไม่แก้ working tree และตรวจ commits ที่กำลังจะนำขึ้น server:

```bash
git fetch origin
git log --oneline --decorate HEAD..origin/02_addweather
git show --stat --oneline --summary origin/02_addweather
```

ควรตรวจว่า commit ล่าสุดมีไฟล์ที่ต้องการ deploy จริง เช่น `app/templates/index.html`,
`app/static/style.css` หรือ source code ที่เกี่ยวข้อง

#### 2.2 หยุด service และสำรอง SQLite

```bash
sudo systemctl stop durian-dashboard
systemctl is-active durian-dashboard
```

ผลที่คาดคือ `inactive` จากนั้นสำรองฐานข้อมูลพร้อมตรวจ checksum:

```bash
backup_file="/opt/durian-dashboard-backups/durian_dashboard_$(date +%Y%m%d_%H%M%S).db"
sudo install -D -m 0640 -o bigdata -g bigdata \
  /opt/durian-dashboard/data/durian_dashboard.db "$backup_file"
echo "BACKUP=$backup_file"
sha256sum /opt/durian-dashboard/data/durian_dashboard.db "$backup_file"
```

checksum ของไฟล์ต้นทางและ backup ต้องตรงกัน เก็บค่า `BACKUP=` ไว้ใช้ในขั้นตอนคืนข้อมูล

#### 2.3 จัดการฐานข้อมูลที่ทำให้ Git conflict

ตรวจสถานะอีกครั้ง:

```bash
cd /opt/durian-dashboard
git status --short --branch
```

ถ้าฐานข้อมูลแสดงเป็น `UU data/durian_dashboard.db` แต่ไม่มี active merge ให้ล้างเฉพาะ
สถานะ conflict ใน staging area โดยไม่แตะไฟล์ฐานข้อมูล:

```bash
git rev-parse -q --verify MERGE_HEAD
git ls-files -u -- data/durian_dashboard.db
git restore --staged data/durian_dashboard.db
```

เมื่อ backup สมบูรณ์และ service หยุดแล้ว ให้คืนฐานข้อมูลใน working tree เป็นเวอร์ชัน Git
ชั่วคราว เพื่อเปิดทางให้ fast-forward pull:

```bash
git restore --worktree data/durian_dashboard.db
git status --short --branch
```

ขั้นตอนนี้เปลี่ยนไฟล์ฐานข้อมูลใน working tree แต่ข้อมูลจริงยังอยู่ใน backup นอก repository

#### 2.4 ดึงโค้ดเวอร์ชันใหม่

```bash
git pull --ff-only origin 02_addweather
```

ใช้ `--ff-only` เพื่อไม่ให้ server สร้าง merge commit โดยไม่ตั้งใจ หากคำสั่งล้มเหลว
ให้หยุดตรวจ `git status` ก่อน ห้ามแก้ด้วย `reset --hard`

#### 2.5 คืนฐานข้อมูลจริง

แทน `<BACKUP_PATH>` ด้วย path จากบรรทัด `BACKUP=` ในขั้นตอนสำรอง:

```bash
sudo install -m 0640 -o bigdata -g bigdata \
  <BACKUP_PATH> /opt/durian-dashboard/data/durian_dashboard.db
sha256sum <BACKUP_PATH> /opt/durian-dashboard/data/durian_dashboard.db
```

checksum ต้องตรงกันก่อนเริ่ม service

#### 2.6 ตรวจ dependencies และโหลดแอป

```bash
cd /opt/durian-dashboard
./.venv/bin/python --version
./.venv/bin/python -m pip check
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -B -c \
  "from app.main import app; print('APP_OK:', app.title, app.version)"
```

ผลบรรทัดสุดท้ายควรขึ้นต้นด้วย `APP_OK:`

#### 2.7 เริ่ม service และตรวจระบบ

```bash
sudo systemctl start durian-dashboard
sleep 3
systemctl is-active durian-dashboard
sudo systemctl status durian-dashboard --no-pager --full
```

service ต้องเป็น `active (running)` และ log ควรแสดงว่า FastAPI, MQTT และ WebSocket
เริ่มทำงานสำเร็จ จากนั้นตรวจหน้าเว็บและ API โดยใช้ port ที่กำหนดใน service
(ตัวอย่างนี้ใช้ `8081`):

```bash
printf 'Dashboard: '
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8081/
printf 'Latest API: '
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8081/api/latest
curl -fsS http://127.0.0.1:8081/api/latest
```

Dashboard และ Latest API ต้องตอบ `200` และ `/api/latest` ควรมีข้อมูล sensor ล่าสุด

ตรวจสถานะ Git หลัง deploy:

```bash
cd /opt/durian-dashboard
git status --short --branch
```

การเห็น `M data/durian_dashboard.db` หลังเปิด service เป็นเรื่องปกติ เพราะ MQTT เขียนข้อมูลใหม่
และ `.venv/` อาจแสดงเป็น untracked หากยังไม่ได้อยู่ใน `.gitignore`

#### 2.8 Rollback เฉพาะฐานข้อมูลเมื่อจำเป็น

หาก service เริ่มไม่ได้เพราะฐานข้อมูลหลัง deploy ให้หยุด service ก่อน แล้วคืน backup:

```bash
sudo systemctl stop durian-dashboard
sudo install -m 0640 -o bigdata -g bigdata \
  <BACKUP_PATH> /opt/durian-dashboard/data/durian_dashboard.db
sudo systemctl start durian-dashboard
sudo systemctl status durian-dashboard --no-pager --full
```

ควรแก้ repository ต่อไปโดยเลิก track `data/durian_dashboard.db`, `.venv/` และ `__pycache__/`
เพื่อป้องกัน conflict และไม่ส่งข้อมูล runtime ขึ้น Git

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
TMD_ACCESS_TOKEN
STATION_LATITUDE
STATION_LONGITUDE
STATION_ALTITUDE_M
STATION_TIMEZONE
WIND_SENSOR_HEIGHT_M
LUX_PER_WM2
ETO_MAX_GAP_MINUTES
```

`TMD_ACCESS_TOKEN` ใช้เรียกข้อมูลพยากรณ์จากกรมอุตุนิยมวิทยาเป็นแหล่งหลัก
หากไม่ได้ตั้งค่า, token หมดอายุ, TMD ตอบ error/timeout หรือไม่มีข้อมูล ระบบจะใช้
Open-Meteo เป็นแหล่งสำรองและระบุแหล่งข้อมูลบนหน้า Dashboard

### การคำนวณ ET0 แบบ FAO-56 รายชั่วโมง

ระบบใช้สมการ FAO-56 Penman-Monteith สำหรับช่วงเวลารายชั่วโมง ซึ่งใช้ค่าคงที่
`37` ไม่ใช่ค่าคงที่ `900` ของสมการรายวัน จากนั้นอินทิเกรตอัตรา `mm/hour`
ตามช่วงเวลาระหว่างข้อมูลที่ได้รับ เพื่อสร้าง `eto_mm_day_est` แบบสะสมตั้งแต่
เวลา 00:00 ของวันใน timezone ของสถานี

ต้องกำหนดพิกัดจริงของสถานีใน `.env` ก่อน ระบบจึงจะคำนวณ ET0:

```bash
STATION_LATITUDE=<latitude ของสถานี>
STATION_LONGITUDE=<longitude ของสถานี>
STATION_ALTITUDE_M=<ความสูงจากระดับทะเล หน่วยเมตร>
STATION_TIMEZONE=Asia/Bangkok
WIND_SENSOR_HEIGHT_M=<ความสูงที่ติดตั้งเซนเซอร์ลม หน่วยเมตร>
```

ถ้าไม่ได้กำหนด latitude หรือ longitude ระบบจะเก็บ `eto_mm_h_est` และ
`eto_mm_day_est` เป็น `null` แทนการแสดงค่าที่อาจทำให้เข้าใจผิด

ข้อจำกัดที่ต้องระบุเมื่อใช้ในงานวิจัย:

- รังสีดวงอาทิตย์ยังประมาณจาก lux โดยใช้ `LUX_PER_WM2` ค่าเริ่มต้น 120
- ควรสอบเทียบค่า `LUX_PER_WM2` กับ pyranometer หรือสถานีอ้างอิงในพื้นที่
- ความเร็วลมถูกปรับเป็นความสูงมาตรฐาน 2 เมตรตาม FAO-56 Equation 47
- หากข้อมูลขาดช่วงนานกว่า `ETO_MAX_GAP_MINUTES` ระบบจะไม่ประมาณ ET0 เติมช่องว่าง
- `eto_mm_day_est` จึงเป็นผลรวมเฉพาะช่วงเวลาที่มีข้อมูลเชื่อมต่อกัน ไม่ใช่ค่าที่เดาเติม

ตรวจสอบสมการด้วยชุดทดสอบ:

```bash
pip install -r requirements-dev.txt
pytest -q
```

ชุดทดสอบอ้างอิง FAO-56 Example 19 ซึ่งให้ผล ET0 ช่วงกลางวันประมาณ
`0.63 mm/hour`

### Data retention policy (local cache)

- ค่าแนะนำสำหรับหน้างานที่มีข้อมูลหลักอยู่บน server: `RETAIN_DAYS=90`
- ระบบจะลบข้อมูลที่เก่ากว่า `RETAIN_DAYS` อัตโนมัติระหว่างรัน (ตรวจทุก ~1 ชั่วโมง)
- สามารถปรับในไฟล์ `.env` ได้ตามต้องการ

## API

- `GET /api/latest`
- `GET /api/history?field=vpd_kpa&hours=24`
- `GET /api/history?field=eto_mm_h_est&hours=24`
- `GET /api/eto/daily?days=7`
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

### Screen timeout (xset/DPMS) usage

ใช้กับ Raspberry Pi ที่รัน X11/Chromium kiosk เพื่อกำหนดเวลาพักหน้าจอหรือดับหน้าจอ

คำสั่งที่ต้องใช้และความหมาย:

- `export DISPLAY=:0`
  - ระบุ X display หลักของเครื่อง (จอที่ kiosk ใช้งานอยู่)
- `export XAUTHORITY=/home/pi/.Xauthority`
  - ระบุไฟล์สิทธิ์เข้าถึง X session ของ user `pi` (ช่วยแก้ปัญหา `unable to open display`)
- `xset s <sec> 0`
  - ตั้ง idle timeout ของ screen saver เป็น `<sec>` วินาที
- `xset +dpms`
  - เปิดการทำงาน DPMS (โหมดประหยัดพลังงานของจอ)
- `xset dpms <standby> <suspend> <off>`
  - ตั้งเวลา DPMS เป็นวินาที
  - หากตั้งค่าเท่ากันทั้ง 3 ค่า เช่น `900 900 900` จะทำให้จอเข้าสถานะพัก/ดับที่เวลาใกล้เคียงกัน

สูตรคำนวณเวลาสำหรับตั้งค่าดับหน้าจอ:

- `T_sec = (ชั่วโมง x 3600) + (นาที x 60) + วินาที`

ตัวอย่างการคำนวณ:

- 5 นาที: `5 x 60 = 300` วินาที
- 15 นาที: `15 x 60 = 900` วินาที
- 1 ชั่วโมง: `1 x 3600 = 3600` วินาที

ตารางแปลงเวลาแบบเร็ว:

| นาที | วินาที (ใช้กับ xset) |
|---:|---:|
| 1  | 60   |
| 3  | 180  |
| 5  | 300  |
| 10 | 600  |
| 15 | 900  |
| 30 | 1800 |
| 60 | 3600 |

### Optional: Quick screen timeout test (20 seconds)

```bash
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority
xset s 20 0
xset +dpms
xset dpms 20 20 20
```

### Example: set screen timeout to 15 minutes

```bash
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority
xset s 900 0
xset +dpms
xset dpms 900 900 900
```

### Restore 1-hour screen timeout

```bash
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority
xset s 3600 0
xset +dpms
xset dpms 3600 3600 3600
```

### Troubleshooting: SQLite error `database disk image is malformed`

หากดู log แล้วพบข้อความนี้ แปลว่าไฟล์ฐานข้อมูล SQLite เสียหาย (ไม่เกี่ยวกับ Wi-Fi โดยตรง)

ตรวจ log:

```bash
sudo journalctl -u durian-dashboard -n 200 --no-pager
```

ระบบเวอร์ชันใหม่จะพยายาม backup และสร้างฐานข้อมูลใหม่ให้อัตโนมัติเมื่อเจอ error นี้

หากยังไม่หาย ให้กู้คืนแบบ manual:

```bash
cd /opt/durian-dashboard
sudo systemctl stop durian-dashboard
mv data/durian_dashboard.db data/durian_dashboard.db.corrupt.$(date +%Y%m%d_%H%M%S)
sudo systemctl start durian-dashboard
```

หมายเหตุ:
- หลังสร้าง DB ใหม่ กราฟย้อนหลังจะเริ่มเก็บข้อมูลใหม่ตั้งแต่เวลาที่ service กลับมารัน
- ข้อมูลไฟล์เก่าจะยังอยู่ในชื่อ `.corrupt.*` สำหรับเก็บไว้ตรวจสอบภายหลัง

## Notes for Pi3

- If upstream server stores long-term data, keep local cache at `RETAIN_DAYS=90`.
- Use one Uvicorn worker.
- Keep MQTT publish interval at 1-5 minutes.
