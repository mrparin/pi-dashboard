#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/durian-dashboard}"
SERVICE_NAME="${SERVICE_NAME:-durian-dashboard}"
PI_USER="${PI_USER:-pi}"
PI_HOME="${PI_HOME:-/home/$PI_USER}"
SERVICE_SRC="$APP_DIR/systemd/$SERVICE_NAME.service"
SERVICE_DST="/etc/systemd/system/$SERVICE_NAME.service"
KIOSK_SCRIPT="$PI_HOME/start-dashboard-kiosk.sh"
AUTOSTART_DIR="$PI_HOME/.config/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/dashboard-kiosk.desktop"
SCREEN_TIMEOUT="${SCREEN_TIMEOUT:-3600}"
DASHBOARD_URL="${DASHBOARD_URL:-http://127.0.0.1:8080}"

log() {
  echo "[setup] $*"
}

warn() {
  echo "[setup][warn] $*" >&2
}

die() {
  echo "[setup][error] $*" >&2
  exit 1
}

require_root() {
  if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    die "Run this script as root: sudo bash scripts/setup_pi_kiosk.sh"
  fi
}

require_paths() {
  [ -d "$APP_DIR" ] || die "APP_DIR not found: $APP_DIR"
  [ -f "$APP_DIR/requirements.txt" ] || die "Missing requirements file: $APP_DIR/requirements.txt"
  [ -f "$SERVICE_SRC" ] || die "Missing service file: $SERVICE_SRC"
  id "$PI_USER" >/dev/null 2>&1 || die "User not found: $PI_USER"
}

install_packages() {
  log "Installing OS packages"
  apt-get update
  apt-get install -y python3-venv python3-pip curl unclutter

  if apt-cache show chromium-browser >/dev/null 2>&1; then
    apt-get install -y chromium-browser
  else
    apt-get install -y chromium
  fi
}

setup_python_env() {
  log "Creating and updating Python virtual environment"
  if [ ! -d "$APP_DIR/.venv" ]; then
    python3 -m venv "$APP_DIR/.venv"
  fi

  "$APP_DIR/.venv/bin/pip" install --upgrade pip
  "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
}

setup_systemd_service() {
  log "Configuring systemd service"
  cp "$SERVICE_SRC" "$SERVICE_DST"
  systemctl daemon-reload
  systemctl enable "$SERVICE_NAME"
  systemctl restart "$SERVICE_NAME"
}

set_desktop_autologin() {
  log "Setting Desktop Autologin"
  if command -v raspi-config >/dev/null 2>&1; then
    if ! raspi-config nonint do_boot_behaviour B4; then
      warn "Could not set Desktop Autologin automatically. Set it manually in raspi-config."
    fi
  else
    warn "raspi-config not found. Set Desktop Autologin manually."
  fi
}

create_kiosk_launcher() {
  log "Creating kiosk launcher script"
  cat > "$KIOSK_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:0
export XAUTHORITY=$PI_HOME/.Xauthority

# Idle for one hour, then blank/power-save display.
xset s $SCREEN_TIMEOUT 0
xset +dpms
xset dpms $SCREEN_TIMEOUT $SCREEN_TIMEOUT $SCREEN_TIMEOUT

# Hide cursor when idle.
unclutter -idle 0.5 -root &

URL="$DASHBOARD_URL"

# Wait until FastAPI is reachable.
until curl -fsS "\$URL" >/dev/null; do
  sleep 2
done

BROWSER="\$(command -v chromium-browser || command -v chromium || true)"
if [ -z "\$BROWSER" ]; then
  echo "Chromium not found" >&2
  exit 1
fi

# Keep browser alive if it gets closed.
while true; do
  "\$BROWSER" \
    --kiosk \
    --incognito \
    --noerrdialogs \
    --disable-session-crashed-bubble \
    --check-for-update-interval=31536000 \
    "\$URL"
  sleep 2
done
EOF

  chmod +x "$KIOSK_SCRIPT"
  chown "$PI_USER:$PI_USER" "$KIOSK_SCRIPT"
}

create_desktop_autostart() {
  log "Creating desktop autostart entry"
  mkdir -p "$AUTOSTART_DIR"

  cat > "$AUTOSTART_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Durian Dashboard Kiosk
Exec=$KIOSK_SCRIPT
X-GNOME-Autostart-enabled=true
EOF

  chown -R "$PI_USER:$PI_USER" "$PI_HOME/.config"
}

print_summary() {
  log "Completed"
  echo
  echo "Next steps:"
  echo "1) Reboot: sudo reboot"
  echo "2) After boot, verify service: sudo systemctl status $SERVICE_NAME --no-pager"
  echo "3) Verify web port: sudo ss -tulpn | grep 8080"
  echo
  echo "Optional quick screen timeout test (20 seconds):"
  echo "export DISPLAY=:0"
  echo "export XAUTHORITY=$PI_HOME/.Xauthority"
  echo "xset s 20 0"
  echo "xset +dpms"
  echo "xset dpms 20 20 20"
  echo
  echo "Restore 1-hour timeout:"
  echo "xset s $SCREEN_TIMEOUT 0"
  echo "xset +dpms"
  echo "xset dpms $SCREEN_TIMEOUT $SCREEN_TIMEOUT $SCREEN_TIMEOUT"
}

main() {
  require_root
  require_paths
  install_packages
  setup_python_env
  setup_systemd_service
  set_desktop_autologin
  create_kiosk_launcher
  create_desktop_autostart
  print_summary
}

main "$@"
