# DeltaDrop Complete Setup Guide

This guide matches the current DeltaDrop project in this workspace.
It does not assume older config names or older frontend behavior.

## Summary

DeltaDrop has:
- A FastAPI backend in `deltadrop-backend`
- A Vite + React frontend in `deltadrop-frontend`
- PostgreSQL as the database

You can use either:
- Local PostgreSQL
- Supabase Postgres

Current bug-fix state already included in the codebase:
- `h2==4.1.0` added for `httpx` HTTP/2 support
- SerpAPI filtering fixed so valid Google Shopping results are not dropped
- Frontend backend-offline cooldown reduced from `5000ms` to `1500ms`
- Product search retries increased from `3` to `5`
- Chart loop fixed and demo history now renders for temporary `search_` results
- Buy Now and product image links now fall back to retailer search pages instead of reopening DeltaDrop

## Prerequisites

Install these first:
- Python `3.11+`
- Node.js `18+`
- PostgreSQL `13+` if using local DB
- Git

Optional but useful:
- Redis

Accounts or API keys you may need:
- `SERPAPI_API_KEY` for reliable product search
- `SCRAPER_API_KEY` optional
- `SCRAPE_DO_API_KEY` optional
- `GEMINI_API_KEY` for AI features
- `GOOGLE_CLIENT_ID` for Google login

## Backend Setup

### 1. Open the backend folder

```powershell
cd C:\Users\nakul\Downloads\deltadrop-project\deltadrop-backend
```

### 2. Create and activate a virtual environment

```powershell
python -m venv venv (py -3.11 -m venv venv)
.\venv\Scripts\activate
```
.\.venv\Scripts\Activate.ps1
cd C:\Users\nakul\Downloads\deltadrop-project\deltadrop-backend
<!-- py -3.14 -m pip install --upgrade pip setuptools wheel
py -3.14 -m pip install Cython meson ninja --> can skip
py -3.14 -m pip install -r requirements.txt
### 3. Install Python dependencies

```powershell
pip install -r requirements.txt
```

Important:
- `requirements.txt` already includes `h2==4.1.0`
- You do not need to install packages one by one if `pip install -r requirements.txt` works

### 4. Install the Playwright browser

```powershell
playwright install chromium - don't install it
``` 

This is required for scraping paths that use Playwright.

### 5. Configure `deltadrop-backend/.env`

Start from the backend example if needed:

```powershell
copy .env.example .env
```

#### Local PostgreSQL example

```env
APP_ENV=development
FRONTEND_ORIGIN=http://localhost:5000

DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/deltadrop
DATABASE_URL_SYNC=postgresql://postgres:password@localhost:5432/deltadrop

JWT_SECRET_KEY=your-long-random-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

ADMIN_EMAIL=admin@deltadrop.in
ADMIN_PASSWORD=YourStrongPassword123!

SERPAPI_API_KEY=your_serpapi_key
SCRAPER_API_KEY=
SCRAPE_DO_API_KEY=

GEMINI_API_KEY=your_gemini_key
GOOGLE_CLIENT_ID=your_google_client_id

REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=900
```

#### Supabase Postgres example

Use Supabase only as the hosted PostgreSQL database unless you intentionally want to rewrite auth.

```env
APP_ENV=development
FRONTEND_ORIGIN=http://localhost:5000

DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@[HOST]:5432/postgres?sslmode=require
DATABASE_URL_SYNC=postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres?sslmode=require

JWT_SECRET_KEY=your-long-random-secret
ADMIN_EMAIL=admin@deltadrop.in
ADMIN_PASSWORD=YourStrongPassword123!

SERPAPI_API_KEY=your_serpapi_key
SCRAPER_API_KEY=
SCRAPE_DO_API_KEY=

GEMINI_API_KEY=your_gemini_key
GOOGLE_CLIENT_ID=your_google_client_id
```

Notes:
- Keep both `DATABASE_URL` and `DATABASE_URL_SYNC` set
- Supabase connections should use `sslmode=require`
- This project still uses its own FastAPI JWT auth, not Supabase Auth

### 6. Create the database if you are using local PostgreSQL

```powershell
createdb deltadrop or psql -U postgres -c "CREATE DATABASE deltadrop;"
```

If `createdb` is not in PATH, create the database from pgAdmin or `psql`.

### 7. Initialize database tables

Recommended with the current project setup:

```powershell
python scripts\init_db.py
```

Alternative:

```powershell
alembic upgrade head
```

Use the Alembic path only if your migration chain is confirmed clean in your environment.
`scripts/init_db.py` is the more practical option for this repo right now.

### 8. Start the backend

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 9. Backend verification

Open these in your browser:

- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:8000/docs`

Expected:
- Health returns status `ok`
- Swagger docs open normally

## Frontend Setup

### 1. Open the frontend folder

```powershell
cd C:\Users\nakul\Downloads\deltadrop-project\deltadrop-frontend
```

### 2. Install frontend dependencies

```powershell
npm install
```

If Windows gives `EPERM`:
- Close terminals or apps that may be locking `node_modules`
- Delete `node_modules`
- Run `npm install` again

### 3. Configure frontend `.env`

Start from the frontend example if needed:

```powershell
copy .env.example .env
```

Use:

```env
VITE_API_BASE=http://127.0.0.1:8000/api/v1
VITE_GOOGLE_CLIENT_ID=your_google_client_id
VITE_GEMINI_API_KEY=
```

Notes:
- This repo uses `VITE_API_BASE`, not `VITE_API_URL`
- The frontend example currently defaults to `/api/v1`; for local development it is better to set the full backend URL explicitly
- Keeping `VITE_GEMINI_API_KEY` empty is safer because `VITE_` variables are exposed in the browser

### 4. Start the frontend

```powershell
npm run dev
```

Current Vite config uses port `5000`, so the app should open at:

- `http://localhost:5000`

## Full Local Run

Use two terminals.

### Terminal 1

```powershell
cd C:\Users\nakul\Downloads\deltadrop-project\deltadrop-backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Terminal 2

```powershell
cd C:\Users\nakul\Downloads\deltadrop-project\deltadrop-frontend
npm run dev
```

## Verification Checklist

### Backend

- PostgreSQL is running
- `pip install -r requirements.txt` completed
- `playwright install chromium` completed
- `.env` is configured
- Backend starts on `8000`
- `http://127.0.0.1:8000/api/health` returns `ok`

### Frontend

- `npm install` completed
- Frontend `.env` uses `VITE_API_BASE`
- Frontend starts on `5000`
- App opens in the browser

### Search and product flow

- Search `h&m wide high waist jeans` and results appear
- Search `adidas ultra boost` and relevant Ultraboost results appear
- Product page does not get stuck on `/product/search_xxx`
- Search results with temporary IDs still show a chart using demo data
- Saved or persisted products show real price history
- Buy Now opens a retailer page, retailer search page, or Google Shopping page, not DeltaDrop itself
- If Playwright or Scrape.do paths fail, SerpAPI results still appear when `SERPAPI_API_KEY` is valid

## Troubleshooting

### `vite` is not recognized

Run:

```powershell
npm install
```

This means frontend dependencies were not installed correctly.

### `npm install` fails with `EPERM`

Common Windows fix:
- Close VS Code terminals using the folder
- Delete `node_modules`
- Retry `npm install`

### Search returns no results

Check:
- `SERPAPI_API_KEY` is valid
- `playwright install chromium` was run
- Backend is actually running on `8000`

Notes:
- `SCRAPE_DO_API_KEY` is optional
- An invalid Scrape.do key should no longer block SerpAPI results

### Product scraping fails

Check:
- Playwright Chromium is installed
- Your API keys are valid
- Target retailer is not actively blocking your IP or requests

### Database connection fails

For local PostgreSQL:
- Confirm PostgreSQL service is running
- Confirm database `deltadrop` exists
- Confirm username, password, host, and port match your `.env`

For Supabase:
- Confirm `DATABASE_URL` and `DATABASE_URL_SYNC` are both correct
- Confirm `sslmode=require` is present

### Frontend cannot reach backend

Check:
- Backend is running on `127.0.0.1:8000`
- Frontend `.env` uses:

```env
VITE_API_BASE=http://127.0.0.1:8000/api/v1
```

- Backend `.env` uses:

```env
FRONTEND_ORIGIN=http://localhost:5000
```

## Important Notes

- Redis is listed in the backend config, but core local setup can still proceed without making Redis the first blocker unless you are using features that depend on it in your environment
- Keep Gemini on the backend when possible instead of exposing a browser key
- Supabase should be treated as the database host only unless you intentionally want a broader integration
- The current frontend dev server port is `5000`, not `5173`

## Quick Commands

### Backend quick start

```powershell
cd C:\Users\nakul\Downloads\deltadrop-project\deltadrop-backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend quick start

```powershell
cd C:\Users\nakul\Downloads\deltadrop-project\deltadrop-frontend
npm run dev
```

## Access URLs

- Frontend: `http://localhost:5000`
- Backend API: `http://127.0.0.1:8000`
- Swagger Docs: `http://127.0.0.1:8000/docs`
