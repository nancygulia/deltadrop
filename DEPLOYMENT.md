# DeltaDrop Deployment Guide

## 1. Database on Railway (Postgres)
- Go to https://railway.app/dashboard
- New Project → Provision PostgreSQL
- Copy `DATABASE_URL` (e.g., `postgresql://user:pass@host:port/db`)

## 2. Backend on Render (FastAPI)
- https://dashboard.render.com/new/web-service
- Connect GitHub repo: nancygulia/deltadrop
- **Root Directory:** `/deltadrop-backend`
- **Runtime:** Python 3
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables:**
  - `DATABASE_URL=postgresql://postgres:jTaoQEskTDbkpevXMBUyOsdgrEgnCPOi@tramway.proxy.rlwy.net:13288/railway`
  - `SECRET_KEY=your-super-secret-key-generate-a-strong-one`
  - `ANTHROPIC_API_KEY=sk-ant-...` (from Anthropic dashboard)
  - `GOOGLE_GENAI_KEY=AIza...` (from Google AI Studio)
- Deploy → URL: https://deltadrop-backend-abc.onrender.com
- Test: https://your-url/api/docs (Swagger UI)

## 3. Frontend on Vercel (React)
- https://vercel.com/new → Import nancygulia/deltadrop
- Root: `/deltadrop-frontend`
- Build: `npm install && npm run build`
- Output: `dist`
- Env: `VITE_API_URL=https://your-render-backend.onrender.com/api`
- Deploy!

## URLs
- Backend API: https://your-backend.onrender.com/api/docs (Swagger)
- Frontend: https://your-vercel-app.vercel.app

Test search/scrape/AI features after deploy.

