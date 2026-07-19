# Durian Dashboard frontend

This is a Next.js static export. In production Nginx serves `out/` at port 8081; it proxies `/api/` and `/ws` to the Python backend on `127.0.0.1:8000`.

## Local development

```bash
cp .env.local.example .env.local
npm install
npm run dev
```

Open `http://localhost:3001`. Start FastAPI separately on port 8000.

## Production build

```bash
npm ci
npm run build
```

Deploy the generated `out/` directory with the Nginx configuration in `../nginx/durian-dashboard.conf`.
