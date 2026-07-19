# คู่มือ Deploy Durian Dashboard บน Ubuntu Server

เอกสารนี้จัดทำจากโครงสร้าง **repo ปัจจุบันบน branch `03_redesign`** (`origin/03_redesign`) โดยกำหนดให้เว็บไซต์เปิดจากพอร์ตที่หน่วยงานอนุญาตคือ `8081` และไม่กระทบ Grafana ที่ใช้พอร์ต `3000`

> Production ต้อง deploy จาก branch `03_redesign` ไม่ใช่ `master`, `01_addicon` หรือ `02_addweather`

## 1. สถาปัตยกรรมที่ใช้บน Production

| ส่วนประกอบ | ตำแหน่ง/พอร์ต | หน้าที่ |
|---|---|---|
| Nginx | `0.0.0.0:8081` | จุดเข้าใช้งานเว็บไซต์จากภายนอก, เสิร์ฟไฟล์ Next.js และทำ Reverse Proxy |
| Next.js frontend | `/opt/durian-dashboard/frontend/out` | ไฟล์ static ที่สร้างด้วย `npm run build` จึงไม่ต้องเปิด Next.js port `3001` บน Production |
| FastAPI backend | `127.0.0.1:8001` | API, WebSocket, รับข้อมูล MQTT และเรียก Weather API |
| Docker service เดิม | `0.0.0.0:8000` | บริการเดิมบน Server จึงสงวนพอร์ตนี้ไว้และไม่ใช้กับ FastAPI |
| Docker service เดิม | `0.0.0.0:80` | บริการเดิมบน Server จึงต้องปิด Nginx default site ที่พยายามใช้พอร์ต 80 |
| SQLite | `/var/lib/durian-dashboard/durian_dashboard.db` | เก็บข้อมูลเซนเซอร์ย้อนหลัง แยกออกจาก Git working tree |
| Grafana | พอร์ต `3000` เดิม | ไม่มีการแก้ไขและไม่ชนกับระบบนี้ |

เส้นทางการทำงาน:

```text
ผู้ใช้ :8081 ──> Nginx ──> frontend/out
                         ├── /api/* ──> FastAPI :8001
                         └── /ws    ──> FastAPI WebSocket :8001

MQTT Broker :1883 ──> FastAPI/MQTT client ──> SQLite
```

> ควรใช้ Uvicorn เพียง `1 worker` เพราะแต่ละ worker จะสร้าง MQTT client ของตัวเอง หากเพิ่มจำนวน worker จะเกิดการ subscribe และบันทึกข้อมูลซ้ำได้

## 2. สิ่งที่ Server ต้องเชื่อมต่อได้

- รับการเชื่อมต่อ TCP ขาเข้าที่พอร์ต `8081`
- เชื่อมต่อ MQTT ขาออกไปยัง `sci-iot.ddns.net:1883` หรือตามค่าที่กำหนด
- เชื่อมต่อ HTTPS ขาออกที่พอร์ต `443` สำหรับ TMD, Open-Meteo และชุดข้อมูลสถานที่ประเทศไทย
- ระหว่างติดตั้ง/อัปเดต Server ต้องเชื่อมต่อ `github.com` และ npm registry ผ่าน HTTPS `443` เพื่อใช้ `git clone`, `git pull` และ `npm ci`
- ไม่จำเป็นต้องเปิดพอร์ต `8001` หรือ `3001` จากภายนอก โดย `8001` ต้อง bind เฉพาะ `127.0.0.1`

## 3. ติดตั้งโปรแกรมที่จำเป็น

ตัวอย่างนี้ใช้ Ubuntu 22.04/24.04 และติดตั้งโปรเจกต์ไว้ที่ `/opt/durian-dashboard`

```bash
sudo apt update
sudo apt install -y git nginx python3 python3-venv python3-pip sqlite3 curl
```

ติดตั้ง Node.js รุ่น `20` ขึ้นไป (แนะนำ Node.js 22) ด้วยวิธีที่หน่วยงานอนุญาต แล้วตรวจสอบ:

```bash
node --version
npm --version
python3 --version
```

หาก Server รองรับ Snap สามารถติดตั้ง Node.js 22 ได้ด้วย:

```bash
sudo snap install node --classic --channel=22
```

## 4. Clone Repository

Clone จาก branch `03_redesign` โดยตรง:

```bash
export APP_DIR=/opt/durian-dashboard
export DEPLOY_USER="$USER"

sudo git clone --branch 03_redesign --single-branch \
  https://github.com/mrparin/pi-dashboard.git "$APP_DIR"
sudo chown -R "$DEPLOY_USER":"$DEPLOY_USER" "$APP_DIR"
cd "$APP_DIR"

git branch --show-current
git status --short
```

ผลจาก `git branch --show-current` ต้องเป็น `03_redesign` ก่อนดำเนินการขั้นต่อไป

ณ เวลาที่จัดทำคู่มือนี้ branch ที่ตรวจสอบคือ:

```text
03_redesign -> origin/03_redesign
commit: 45aec9a (fix UI)
```

commit จะเปลี่ยนได้เมื่อมีการ push รุ่นใหม่ แต่ชื่อ branch สำหรับ Production ต้องยังเป็น `03_redesign`

หากภายหลังเปลี่ยน repo เป็น Private Repository ให้ตั้งค่า SSH key หรือ access token ตามนโยบายของหน่วยงานก่อนใช้ `git clone`

## 5. ตั้งค่า Python Backend และ MQTT

สร้าง virtual environment และติดตั้ง dependencies:

```bash
cd /opt/durian-dashboard
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
mkdir -p data
sudo mkdir -p /var/lib/durian-dashboard
sudo chown "$USER":"$USER" /var/lib/durian-dashboard
```

สร้างไฟล์ environment จากตัวอย่าง:

```bash
cp .env.example .env
nano .env
```

ตัวอย่างค่าบน Production:

```dotenv
MQTT_HOST=sci-iot.ddns.net
MQTT_PORT=1883
MQTT_TOPIC=durian_farm1/node_sensor
MQTT_QOS=1

DB_PATH=/var/lib/durian-dashboard/durian_dashboard.db
RETAIN_DAYS=90

APP_HOST=127.0.0.1
APP_PORT=8001
REFRESH_SECONDS=3
FRONTEND_ORIGINS=http://SERVER_IP_OR_DOMAIN:8081

# ใส่ token เมื่อได้รับสิทธิ์ใช้งาน TMD; หากเว้นว่างระบบจะใช้ Open-Meteo
TMD_ACCESS_TOKEN=
```

แทนที่ `SERVER_IP_OR_DOMAIN` ด้วย IP หรือชื่อโดเมนจริง ห้าม commit ไฟล์ `.env` หรือ TMD token เข้า Git จากนั้นจำกัดสิทธิ์ไฟล์:

```bash
chmod 600 /opt/durian-dashboard/.env
```

> MQTT client ใน repo ปัจจุบันยังไม่มีตัวแปร username/password หาก Broker เปิด authentication ต้องเพิ่มการรองรับในโค้ดก่อน deploy

> repo ปัจจุบันมีไฟล์ `.db` ภายใต้ `data/` ที่ถูก Git ติดตาม จึงไม่ควรใช้เป็นฐานข้อมูล Production การแยกฐานข้อมูลไปไว้ที่ `/var/lib/durian-dashboard` ทำให้การอัปเดตหรือ rollback โค้ดไม่แตะต้องข้อมูลจริง

## 6. Build Next.js Frontend

Frontend ใช้ `output: "export"` และจะสร้างไฟล์ production ใน `frontend/out`

```bash
cd /opt/durian-dashboard/frontend
npm ci
npm run build
test -f out/index.html && echo "Frontend build OK"
```

หาก `npm ci` ค้างหรือ timeout ให้ตรวจ DNS, proxy และการเชื่อมต่อ HTTPS ไปยัง npm registry ก่อน ไม่ควรเปลี่ยนไปใช้ `npm install` เพื่อหลีกเลี่ยง lockfile เพราะ Production ควรติดตั้งตาม `package-lock.json`

ไม่ต้องรัน `npm run dev` หรือ `npm start` บน Production และไม่ต้องเปิดพอร์ต `3001` เพราะ Nginx จะเสิร์ฟไฟล์จาก `frontend/out` โดยตรง

อย่ากำหนด `NEXT_PUBLIC_API_BASE` เป็น `http://127.0.0.1:8001` สำหรับ browser ของผู้ใช้ ระบบปัจจุบันออกแบบให้ frontend เรียก `/api` และ `/ws` ผ่าน Nginx แบบ same-origin

## 7. ติดตั้ง Systemd Service

ไฟล์ใน repo กำหนด user เริ่มต้นเป็น `pi` จึงต้องเปลี่ยนให้ตรงกับ user ที่ใช้ deploy:

```bash
export DEPLOY_USER="$USER"

sudo cp /opt/durian-dashboard/systemd/durian-dashboard.service \
  /etc/systemd/system/durian-dashboard.service

sudo sed -i "s/^User=.*/User=$DEPLOY_USER/" \
  /etc/systemd/system/durian-dashboard.service
sudo sed -i "s/^Group=.*/Group=$DEPLOY_USER/" \
  /etc/systemd/system/durian-dashboard.service

# Server นี้มี Docker ใช้ 8000 อยู่แล้ว จึงย้าย FastAPI ไป 127.0.0.1:8001
sudo sed -i \
  's/--host 127.0.0.1 --port 8000/--host 127.0.0.1 --port 8001/' \
  /etc/systemd/system/durian-dashboard.service

# ใช้ .env เป็นแหล่ง configuration หลัก แทน Environment= ที่ hardcode ใน unit เดิม
sudo sed -i '/^Environment=/d' /etc/systemd/system/durian-dashboard.service
sudo sed -i '/^WorkingDirectory=/a EnvironmentFile=/opt/durian-dashboard/.env' \
  /etc/systemd/system/durian-dashboard.service
```

Broker ของโปรเจกต์เป็น Server ภายนอก จึงสามารถเปลี่ยน dependency จาก Mosquitto ภายในเครื่องเป็น network-online:

```bash
sudo sed -i \
  -e 's/^After=.*/After=network-online.target/' \
  -e 's/^Wants=.*/Wants=network-online.target/' \
  /etc/systemd/system/durian-dashboard.service
```

ตรวจสอบคำสั่งสำคัญใน service:

```text
WorkingDirectory=/opt/durian-dashboard
ExecStart=/opt/durian-dashboard/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 1
```

เปิดใช้งานและเริ่ม backend:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now durian-dashboard
sudo systemctl status durian-dashboard --no-pager --full
```

ทดสอบ FastAPI โดยตรงจากภายใน Server:

```bash
curl -fsS http://127.0.0.1:8001/api/health
curl -fsS http://127.0.0.1:8001/api/latest
```

## 8. ติดตั้ง Nginx ที่พอร์ต 8081

คัดลอก configuration จาก repo แล้วเปลี่ยน backend upstream จากค่าเริ่มต้น `8000` เป็น `8001`:

```bash
sudo cp /opt/durian-dashboard/nginx/durian-dashboard.conf \
  /etc/nginx/sites-available/durian-dashboard

sudo sed -i \
  's#proxy_pass http://127.0.0.1:8000#proxy_pass http://127.0.0.1:8001#g' \
  /etc/nginx/sites-available/durian-dashboard

# Docker ใช้ port 80 อยู่ จึงปิดเฉพาะ default site ของ Nginx
if [ -L /etc/nginx/sites-enabled/default ]; then
  sudo unlink /etc/nginx/sites-enabled/default
fi

sudo ln -sfn /etc/nginx/sites-available/durian-dashboard \
  /etc/nginx/sites-enabled/durian-dashboard

sudo nginx -t
sudo systemctl reset-failed nginx
sudo systemctl enable --now nginx
```

หากใช้ UFW ให้เปิดเฉพาะพอร์ตที่ได้รับอนุญาต:

```bash
sudo ufw allow 8081/tcp
sudo ufw status
```

ไม่ต้องเปิด `8001/tcp` และ `3001/tcp` โดยพอร์ต `8000` และ `80` ยังคงเป็นของ Docker เดิม

## 9. ตรวจสอบหลัง Deploy

รันจาก Ubuntu Server:

```bash
curl -I http://127.0.0.1:8081/
curl -fsS http://127.0.0.1:8081/api/health
curl -fsS http://127.0.0.1:8081/api/latest
sudo ss -lntp | grep -E ':8081|:8001|:8000|:3000|:80\s'
```

ผลที่ควรได้:

- หน้า `/` ตอบกลับ `200`
- `/api/health` แสดง `{"status":"ok", ...}`
- Nginx listen ที่ `0.0.0.0:8081`
- Uvicorn listen เฉพาะ `127.0.0.1:8001`
- Docker ยังคงใช้พอร์ต `8000` และ `80`
- Grafana ยังคงใช้พอร์ต `3000`
- เมื่อ MQTT ส่งข้อมูล `/api/latest` ต้องมี timestamp และค่าเซนเซอร์ล่าสุด

เปิดจากเครื่องผู้ใช้:

```text
http://SERVER_IP_OR_DOMAIN:8081
```

ตรวจ log การเชื่อมต่อ MQTT:

```bash
sudo journalctl -u durian-dashboard -n 100 --no-pager
sudo journalctl -u durian-dashboard -f
```

ควรพบข้อความลักษณะ `Connected to MQTT broker` และ `Subscribed topic`

## 10. ขั้นตอนอัปเดตเวอร์ชันภายหลัง

### 10.1 สำรองฐานข้อมูลก่อนอัปเดต

การใช้ SQLite `.backup` สามารถสร้าง snapshot ที่สอดคล้องกันได้โดยไม่คัดลอกไฟล์ฐานข้อมูลแบบดิบ:

```bash
sudo mkdir -p /opt/durian-dashboard-backups
sudo chown "$USER":"$USER" /opt/durian-dashboard-backups

BACKUP_FILE="/opt/durian-dashboard-backups/durian_dashboard_$(date +%Y%m%d_%H%M%S).db"
sqlite3 /var/lib/durian-dashboard/durian_dashboard.db ".backup '$BACKUP_FILE'"
sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;"
echo "$BACKUP_FILE"
```

ผล `PRAGMA integrity_check;` ต้องเป็น `ok`

### 10.2 ดึงโค้ดและ Build ใหม่

ฐานข้อมูล Production ถูกแยกไว้ที่ `/var/lib/durian-dashboard` แล้ว จึงสามารถตรวจและอัปเดต working tree ได้โดยไม่เขียนทับข้อมูลจริง:

```bash
cd /opt/durian-dashboard
git fetch origin
git switch 03_redesign
git status --short
git pull --ff-only origin 03_redesign
test "$(git branch --show-current)" = "03_redesign" && echo "Branch OK"

.venv/bin/pip install -r requirements.txt

cd frontend
npm ci
npm run build
```

### 10.3 Restart เฉพาะส่วนที่เปลี่ยน

```bash
sudo cp /opt/durian-dashboard/systemd/durian-dashboard.service \
  /etc/systemd/system/durian-dashboard.service
```

หลังคัดลอก service ใหม่ ต้องแก้ `User`, `Group` และ dependency network ตามขั้นตอนที่ 7 อีกครั้ง จากนั้นรัน:

```bash
sudo systemctl daemon-reload
sudo systemctl restart durian-dashboard
sudo nginx -t && sudo systemctl reload nginx

curl -fsS http://127.0.0.1:8081/api/health
curl -I http://127.0.0.1:8081/
```

หากเปลี่ยนเฉพาะ frontend หลัง `npm run build` ไม่จำเป็นต้อง restart Python; Nginx จะอ่านไฟล์ใหม่จาก `frontend/out`

## 11. การคืนฐานข้อมูลจาก Backup

ใช้เมื่อฐานข้อมูลเสียหายหรือการอัปเดตมีปัญหา โดยแทนที่ `<BACKUP_FILE>` ด้วยไฟล์ที่ตรวจสอบแล้ว:

```bash
sudo systemctl stop durian-dashboard
cp /var/lib/durian-dashboard/durian_dashboard.db \
  /var/lib/durian-dashboard/durian_dashboard.before_restore.db
cp <BACKUP_FILE> /var/lib/durian-dashboard/durian_dashboard.db
sudo chown "$USER":"$USER" /var/lib/durian-dashboard/durian_dashboard.db
sqlite3 /var/lib/durian-dashboard/durian_dashboard.db "PRAGMA integrity_check;"
sudo systemctl start durian-dashboard
```

## 12. การแก้ปัญหาที่พบบ่อย

### Backend เริ่มไม่ได้

```bash
sudo systemctl status durian-dashboard --no-pager --full
sudo journalctl -u durian-dashboard -n 200 --no-pager
/opt/durian-dashboard/.venv/bin/python -c "from app.config import settings; print(settings)"
```

ให้รันคำสั่ง Python จาก `/opt/durian-dashboard` เพื่อให้ import package `app` และอ่าน `.env` ได้ถูกต้อง

### หน้าเว็บเปิดได้ แต่ API ใช้งานไม่ได้

```bash
curl -v http://127.0.0.1:8001/api/health
curl -v http://127.0.0.1:8081/api/health
sudo nginx -t
sudo tail -n 100 /var/log/nginx/error.log
```

### WebSocket ไม่อัปเดตข้อมูล

ตรวจว่า location `/ws` ใน Nginx มี `proxy_http_version 1.1`, `Upgrade` และ `Connection "upgrade"` ตามไฟล์ใน repo และตรวจ browser console ร่วมกับ:

```bash
sudo journalctl -u durian-dashboard -f
```

### ไม่ได้รับข้อมูล MQTT

```bash
getent hosts sci-iot.ddns.net
nc -vz sci-iot.ddns.net 1883
sudo journalctl -u durian-dashboard | grep -E 'MQTT|Connected|Subscribed|disconnect'
```

หากไม่มีคำสั่ง `nc` ให้ติดตั้งแพ็กเกจ `netcat-openbsd`

### พอร์ตชน

```bash
sudo ss -lntp | grep -E ':8081|:8001|:8000|:3001|:3000|:80\s'
```

- `8081` ต้องเป็น Nginx
- `8001` ต้องเป็น Uvicorn และ bind เฉพาะ localhost
- `8000` และ `80` เป็น Docker service เดิม
- `3000` เป็น Grafana เดิม
- Production ไม่ควรมี process listen ที่ `3001`

## 13. Checklist ก่อนส่งมอบ

- [ ] `npm run build` สำเร็จและมี `frontend/out/index.html`
- [ ] `git branch --show-current` แสดง `03_redesign`
- [ ] `.env` ตั้ง MQTT, database path, frontend origin และ TMD token ถูกต้อง
- [ ] `.env` มี permission `600` และไม่ถูก commit
- [ ] `durian-dashboard.service` ใช้ user/group ที่มีสิทธิ์เขียน `/var/lib/durian-dashboard`
- [ ] Systemd อ่าน configuration จาก `/opt/durian-dashboard/.env` และไม่มี `Environment=` เก่าค้างอยู่
- [ ] Uvicorn ใช้ `--workers 1` และ listen ที่ `127.0.0.1:8001`
- [ ] Nginx default site ถูกปิด เพื่อไม่ให้ชน Docker ที่พอร์ต `80`
- [ ] Nginx listen ที่พอร์ต `8081`
- [ ] Firewall เปิดเฉพาะพอร์ตที่ได้รับอนุญาต
- [ ] `/api/health`, `/api/latest` และหน้าเว็บตอบกลับสำเร็จ
- [ ] MQTT เชื่อมต่อและมีข้อมูลใหม่ใน dashboard
- [ ] กราฟย้อนหลัง, cascading location และพยากรณ์อากาศทำงาน
- [ ] Grafana ที่พอร์ต `3000` ยังทำงานตามเดิม
- [ ] สร้างและตรวจสอบ backup ของ SQLite แล้ว

## 14. ขั้นตอนการรันสคริปต์ `deploy.sh`

หลัง Clone repo และติดตั้ง Node.js 20 ขึ้นไปแล้ว สามารถให้ script ดำเนินการติดตั้ง Python, build frontend, สำรอง SQLite, ติดตั้ง systemd/Nginx และตรวจ health ได้

### 14.1 อัปเดตโค้ดจาก branch ที่ใช้ Production

```bash
cd /opt/durian-dashboard
git fetch origin
git switch 03_redesign
git pull --ff-only origin 03_redesign
git branch --show-current
```

ผลของคำสั่งสุดท้ายต้องเป็น `03_redesign`

### 14.2 ให้สิทธิ์และรันสคริปต์

```bash
chmod +x deploy.sh
./deploy.sh
```

ต้องรันด้วย deployment user ปกติ เช่น `bigdata` ไม่ใช่ `sudo ./deploy.sh` เพราะ script จะเรียก `sudo` เฉพาะคำสั่งที่จำเป็นเอง

หากไม่ต้องการเปลี่ยน permission สามารถรันได้ด้วย:

```bash
bash /opt/durian-dashboard/deploy.sh
```

### 14.3 ข้อกำหนดก่อนรัน

- repo ต้องอยู่ที่ `/opt/durian-dashboard`
- branch ต้องเป็น `03_redesign`
- tracked files ต้องไม่มีการแก้ไขค้างอยู่
- Node.js ต้องเป็นรุ่น 20 ขึ้นไป
- Server ต้องเชื่อมต่อ GitHub และ npm registry ผ่าน HTTPS ได้
- หากมี `.env` อยู่แล้ว ค่า `DB_PATH` ต้องเป็น `/var/lib/durian-dashboard/durian_dashboard.db`
- script ไม่เปิด Firewall ให้อัตโนมัติ ให้เปิด `8081/tcp` ตามนโยบายของหน่วยงานแยกต่างหาก

หากเป็นการติดตั้งครั้งแรก script จะสร้าง `.env` จาก `.env.example` ให้ตรวจค่า MQTT และใส่ `TMD_ACCESS_TOKEN` หลังรัน จากนั้นรัน `./deploy.sh` ซ้ำเพื่อ restart ระบบด้วยค่าล่าสุด

### 14.4 ตรวจสอบหลังสคริปต์ทำงานเสร็จ

```bash
curl -I http://127.0.0.1:8081/
curl -i http://127.0.0.1:8081/api/health
sudo systemctl status durian-dashboard --no-pager --full
sudo systemctl status nginx --no-pager --full
sudo ss -lntp | grep -E ':8081|:8001|:8000|:3000|:80\s'
```

หน้าเว็บและ `/api/health` ต้องตอบ `200 OK`, Nginx ต้องใช้พอร์ต `8081` และ Uvicorn ต้องใช้ `127.0.0.1:8001`
