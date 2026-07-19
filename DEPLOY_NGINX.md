# Deploy with Next.js, FastAPI, and Nginx

This deployment keeps the public port approved for the dashboard: **8081**. Grafana remains on port 3000.

## Service layout

| Service | Address | Purpose |
|---|---|---|
| Nginx | `0.0.0.0:8081` | Public web entry point |
| FastAPI + MQTT | `127.0.0.1:8000` | API, WebSocket, MQTT ingestion |
| Grafana | existing `:3000` | Unchanged |

## First deployment on the server

1. Install Nginx and Node.js 20 or newer.
2. Build the frontend from `/opt/durian-dashboard/frontend`:

   ```bash
   npm ci
   npm run build
   ```

3. Copy `nginx/durian-dashboard.conf` to `/etc/nginx/sites-available/durian-dashboard`, enable it, then validate it:

   ```bash
   sudo ln -s /etc/nginx/sites-available/durian-dashboard /etc/nginx/sites-enabled/durian-dashboard
   sudo nginx -t
   ```

4. Install the updated `systemd/durian-dashboard.service`, reload systemd, and restart the backend:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart durian-dashboard
   sudo systemctl reload nginx
   ```

5. Check both layers:

   ```bash
   curl -fsS http://127.0.0.1:8000/api/health
   curl -I http://127.0.0.1:8081/
   curl -fsS http://127.0.0.1:8081/api/latest
   ```

Do not stop the Python service while it is writing MQTT data. Follow the SQLite backup procedure in `README.md` before any maintenance that requires stopping it.
