# DeltaDrop — Price Intelligence Platform

## Overview
DeltaDrop is a full-stack price tracking and intelligence platform for the Indian e-commerce market. Users can track prices across retailers (Amazon.in, Flipkart, Myntra, etc.), receive alerts, and get ML-powered price predictions.

## Architecture

### Backend (`deltadrop-backend/`)
- **Framework:** FastAPI (Python 3.11) on port 8000
- **Database:** PostgreSQL (Replit managed) via SQLAlchemy 2.0 Async + asyncpg
- **Auth:** JWT tokens with bcrypt password hashing
- **Scraping:** Playwright, BeautifulSoup, curl-cffi
- **ML:** scikit-learn (RandomForest + Gradient Boosting ensemble)
- **Scheduling:** APScheduler with 4 background jobs
- **Entry point:** `app/main.py` via uvicorn

### Frontend (`deltadrop-frontend/`)
- **Framework:** React 18 + Vite on port 5000
- **Styling:** Tailwind CSS
- **Charts:** Chart.js + Recharts
- **API:** Relative path `/api/v1` proxied by Vite to backend at `http://127.0.0.1:8000`

## Workflows
- **Backend API** — `bash start_backend.sh` → initializes DB, starts uvicorn on port 8000 (console)
- **Start application** — `bash start_frontend.sh` → runs `npm run dev` in deltadrop-frontend on port 5000 (webview)

## Database
- Replit managed PostgreSQL
- Tables auto-created on backend startup via `scripts/init_db.py`
- Default admin: `admin@deltadrop.in` / `Admin@123!`

## Key Config Files
- `deltadrop-backend/app/core/config.py` — all backend settings (reads from env)
- `deltadrop-backend/app/db/session.py` — DB engine (strips sslmode from Replit URL for asyncpg)
- `deltadrop-frontend/.env` — frontend env vars (`VITE_API_BASE=/api/v1`)
- `deltadrop-frontend/vite.config.js` — port 5000, host 0.0.0.0, proxy /api → :8000

## Environment Variables
Set automatically by Replit: `DATABASE_URL`, `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
The backend startup script converts `DATABASE_URL` to `postgresql+asyncpg://` format for async SQLAlchemy.
