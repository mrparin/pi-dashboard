#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/opt/durian-dashboard"
EXPECTED_BRANCH="03_redesign"
BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8001"
PUBLIC_PORT="8081"
DB_DIR="/var/lib/durian-dashboard"
DB_PATH="$DB_DIR/durian_dashboard.db"
BACKUP_DIR="/opt/durian-dashboard-backups"
SERVICE_NAME="durian-dashboard"
NGINX_SITE="durian-dashboard"

log() { printf '\n==> %s\n' "$*"; }
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

on_error() {
  local line="$1"
  printf '\nDeploy failed near line %s. Useful logs:\n' "$line" >&2
  printf '  sudo systemctl status %s --no-pager --full\n' "$SERVICE_NAME" >&2
  printf '  sudo journalctl -u %s -n 100 --no-pager\n' "$SERVICE_NAME" >&2
  printf '  sudo journalctl -u nginx -n 100 --no-pager\n' >&2
}
trap 'on_error "$LINENO"' ERR

[[ "$(uname -s)" == "Linux" ]] || die "This script supports Linux/Ubuntu only."
[[ "$EUID" -ne 0 ]] || die "Run as the deployment user, not root: bash deploy.sh"
[[ -d "$APP_DIR/.git" ]] || die "Repository must be located at $APP_DIR"

cd "$APP_DIR"
DEPLOY_USER="$(id -un)"
DEPLOY_GROUP="$(id -gn)"

command -v sudo >/dev/null || die "sudo is required"
command -v git >/dev/null || die "git is required"
command -v python3 >/dev/null || die "python3 is required"
command -v node >/dev/null || die "Node.js 20 or newer is required"
command -v npm >/dev/null || die "npm is required"

NODE_MAJOR="$(node --version | sed -E 's/^v([0-9]+).*/\1/')"
[[ "$NODE_MAJOR" =~ ^[0-9]+$ ]] || die "Cannot determine Node.js version"
(( NODE_MAJOR >= 20 )) || die "Node.js 20 or newer is required; found $(node --version)"

CURRENT_BRANCH="$(git branch --show-current)"
[[ "$CURRENT_BRANCH" == "$EXPECTED_BRANCH" ]] || die "Expected branch $EXPECTED_BRANCH, found $CURRENT_BRANCH"

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  die "Tracked files have local changes. Commit or stash them before deployment."
fi

log "Deploying branch $CURRENT_BRANCH at commit $(git rev-parse --short HEAD)"

log "Installing required Ubuntu packages"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  nginx python3-venv python3-pip sqlite3 curl

log "Preparing persistent database directory"
sudo install -d -o "$DEPLOY_USER" -g "$DEPLOY_GROUP" -m 0750 "$DB_DIR"
sudo install -d -o "$DEPLOY_USER" -g "$DEPLOY_GROUP" -m 0750 "$BACKUP_DIR"

if [[ -f "$DB_PATH" ]]; then
  BACKUP_FILE="$BACKUP_DIR/durian_dashboard_$(date +%Y%m%d_%H%M%S).db"
  log "Backing up SQLite to $BACKUP_FILE"
  sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"
  [[ "$(sqlite3 "$BACKUP_FILE" 'PRAGMA integrity_check;')" == "ok" ]] \
    || die "SQLite backup integrity check failed"
fi

log "Preparing environment configuration"
if [[ ! -f .env ]]; then
  cp .env.example .env
  sed -i \
    -e "s#^DB_PATH=.*#DB_PATH=$DB_PATH#" \
    -e "s#^APP_HOST=.*#APP_HOST=$BACKEND_HOST#" \
    -e "s#^APP_PORT=.*#APP_PORT=$BACKEND_PORT#" \
    .env
  chmod 600 .env
  log "Created .env from .env.example; review MQTT and TMD settings after deployment"
else
  chmod 600 .env
  grep -q "^DB_PATH=$DB_PATH$" .env \
    || die ".env must contain DB_PATH=$DB_PATH"
fi

log "Installing Python dependencies"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python -c "import fastapi, uvicorn, httpx, dotenv, paho.mqtt.client; from app.main import app; print(app.title)"

log "Installing and building Next.js frontend"
cd "$APP_DIR/frontend"
npm ci
npm run build
[[ -f out/index.html ]] || die "Frontend build did not create frontend/out/index.html"
cd "$APP_DIR"

log "Installing systemd service on $BACKEND_HOST:$BACKEND_PORT"
sudo cp systemd/durian-dashboard.service "/etc/systemd/system/$SERVICE_NAME.service"
sudo sed -i \
  -e "s/^User=.*/User=$DEPLOY_USER/" \
  -e "s/^Group=.*/Group=$DEPLOY_GROUP/" \
  -e 's/^After=.*/After=network-online.target/' \
  -e 's/^Wants=.*/Wants=network-online.target/' \
  -e '/^Environment=/d' \
  -e "s/--host [^ ]* --port [0-9]*/--host $BACKEND_HOST --port $BACKEND_PORT/" \
  "/etc/systemd/system/$SERVICE_NAME.service"

if ! sudo grep -q '^EnvironmentFile=/opt/durian-dashboard/.env$' "/etc/systemd/system/$SERVICE_NAME.service"; then
  sudo sed -i '/^WorkingDirectory=/a EnvironmentFile=/opt/durian-dashboard/.env' \
    "/etc/systemd/system/$SERVICE_NAME.service"
fi

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

log "Waiting for FastAPI health check"
BACKEND_READY=0
for _ in {1..20}; do
  if curl -fsS "http://$BACKEND_HOST:$BACKEND_PORT/api/health" >/dev/null; then
    BACKEND_READY=1
    break
  fi
  sleep 1
done
[[ "$BACKEND_READY" -eq 1 ]] || die "FastAPI did not become healthy on $BACKEND_HOST:$BACKEND_PORT"

log "Installing Nginx site on public port $PUBLIC_PORT"
sudo cp nginx/durian-dashboard.conf "/etc/nginx/sites-available/$NGINX_SITE"
sudo sed -i \
  -e "s/listen 8081;/listen $PUBLIC_PORT;/" \
  -e "s#proxy_pass http://127.0.0.1:8000#proxy_pass http://$BACKEND_HOST:$BACKEND_PORT#g" \
  "/etc/nginx/sites-available/$NGINX_SITE"

# Docker already owns port 80 on this server. Disable only Nginx's default site.
if [[ -L /etc/nginx/sites-enabled/default ]]; then
  sudo unlink /etc/nginx/sites-enabled/default
fi

sudo ln -sfn "/etc/nginx/sites-available/$NGINX_SITE" \
  "/etc/nginx/sites-enabled/$NGINX_SITE"
sudo nginx -t
sudo systemctl reset-failed nginx
sudo systemctl enable nginx
sudo systemctl restart nginx

log "Running final checks"
curl -fsSI "http://127.0.0.1:$PUBLIC_PORT/" >/dev/null
curl -fsS "http://127.0.0.1:$PUBLIC_PORT/api/health"
printf '\n'
sudo ss -lntp | grep -E ":$PUBLIC_PORT|:$BACKEND_PORT|:8000|:3000|:80[[:space:]]" || true

log "Deployment completed successfully"
printf 'Website: http://SERVER_IP:%s\n' "$PUBLIC_PORT"
printf 'Branch:  %s\n' "$CURRENT_BRANCH"
printf 'Commit:  %s\n' "$(git rev-parse --short HEAD)"
printf 'Logs:    sudo journalctl -u %s -f\n' "$SERVICE_NAME"
