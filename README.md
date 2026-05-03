# DeltaDrop — Full-Stack Price Intelligence Platform

> ShopSavvy-style price tracking for the Indian market.
> Real-time scraping · ML predictions · AI recommendations · JWT auth.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  React + Vite Frontend  (delta-drop-react/)                 │
│  Tailwind CSS · Chart.js · Claude AI Drawer                 │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API (http://localhost:8000/api/v1)
┌───────────────────────▼─────────────────────────────────────┐
│  FastAPI Backend  (deltadrop-backend/)                      │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │   Auth   │  │ Products │  │   AI     │  │  Admin    │  │
│  │  JWT+    │  │ Scrape   │  │ Claude   │  │  Stats    │  │
│  │  bcrypt  │  │ Predict  │  │ claude-  │  │  Trigger  │  │
│  └──────────┘  └──────────┘  │ sonnet-  │  └───────────┘  │
│                               │ 4-6      │                  │
│  ┌─────────────────────────┐  └──────────┘                  │
│  │     APScheduler         │                                │
│  │  scrape(2h) pred(6h)    │                                │
│  │  alerts(30m) cleanup(d) │                                │
│  └─────────────────────────┘                                │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │   Playwright     │  │  scikit-learn     │               │
│  │  Amazon.in       │  │  RandomForest +   │               │
│  │  Flipkart        │  │  GradientBoosting │               │
│  │  Myntra          │  │  BUY/WAIT verdict │               │
│  │  Reliance Digital│  └──────────────────┘                │
│  │  Nykaa           │                                      │
│  └──────────────────┘                                      │
│                                                             │
│  PostgreSQL — price_history (append-only time-series)       │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

```bash
# Python 3.11+, Node 18+, PostgreSQL 15+
psql -U postgres -c "CREATE DATABASE deltadrop;"
```

### 1 — Backend

```bash
cd deltadrop-backend

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Edit .env: set DATABASE_URL, JWT_SECRET_KEY, ANTHROPIC_API_KEY

python scripts/init_db.py        # create tables + seed admin
python scripts/seed_products.py  # seed 8 products × 90 days price history

uvicorn app.main:app --reload --port 8000
```

✅ API live at **http://localhost:8000**
📖 Swagger UI at **http://localhost:8000/docs**

### 2 — Frontend

```bash
cd delta-drop-react

cp .env.example .env   # VITE_API_BASE=http://localhost:8000/api/v1
npm install
npm run dev
```

✅ App live at **http://localhost:5173**

---

## Default Credentials

After `python scripts/init_db.py`:

| Field    | Value               |
|----------|---------------------|
| Email    | admin@deltadrop.in  |
| Password | Admin@123!          |
| Role     | admin               |

> Change via PATCH `/api/v1/auth/me/password` after first login.

---

## Full API Reference

### Auth — `/api/v1/auth`

| Method | Path              | Auth | Description                  |
|--------|-------------------|------|------------------------------|
| POST   | `/register`       | ✗    | Create account               |
| POST   | `/login`          | ✗    | Returns access + refresh JWT |
| POST   | `/refresh`        | ✗    | Rotate tokens                |
| POST   | `/logout`         | ✗    | Revoke refresh token         |
| GET    | `/me`             | ✓    | Current user profile         |
| PATCH  | `/me/password`    | ✓    | Change password              |

### Products — `/api/v1/products`

| Method | Path                        | Description                              |
|--------|-----------------------------|------------------------------------------|
| GET    | `/`                         | List tracked products (paginated)        |
| POST   | `/track`                    | Add URL → triggers immediate scrape      |
| POST   | `/search`                   | Live search across all retailers         |
| GET    | `/{id}`                     | Product detail + all retailer prices     |
| GET    | `/{id}/price-history`       | Time-series data for Chart.js (7/30/90d) |
| GET    | `/{id}/prediction`          | Latest ML prediction                     |
| POST   | `/{id}/predict`             | Queue fresh prediction (background)      |

### Watchlist & Alerts — `/api/v1`

| Method | Path                | Description              |
|--------|---------------------|--------------------------|
| GET    | `/watchlist`        | User's saved products    |
| POST   | `/watchlist`        | Add product to watchlist |
| DELETE | `/watchlist/{id}`   | Remove from watchlist    |
| GET    | `/alerts`           | User's price alerts      |
| POST   | `/alerts`           | Create price alert       |
| DELETE | `/alerts/{id}`      | Delete alert             |

### AI — `/api/v1/ai`

| Method | Path      | Description                                    |
|--------|-----------|------------------------------------------------|
| POST   | `/ask`    | Claude claude-sonnet-4-6 price recommendation grounded in live data |
| GET    | `/status` | Check API key configured + model status        |

**Request body for `/ai/ask`:**
```json
{
  "product_context": "=== DELTADROP PRODUCT DATA ===\n...",
  "question": "Should I buy now or wait for Diwali?"
}
```

### Admin — `/api/v1/admin`

| Method | Path                      | Description                  |
|--------|---------------------------|------------------------------|
| GET    | `/stats`                  | Platform-wide stats          |
| POST   | `/trigger`                | Manually run scheduler job   |
| GET    | `/users`                  | List all users               |
| PATCH  | `/users/{id}/toggle`      | Enable / disable user        |

---

## Database Schema

```
users
  id, email, username, password_hash, full_name, role, is_active

refresh_tokens
  id, user_id, token_hash, expires_at, revoked

products
  id, name, slug, brand, category, description, image_url, specs, is_active

retailer_listings                          ← one product × many retailers
  id, product_id, retailer, retailer_url,
  current_price, mrp, in_stock, last_scraped_at, scrape_errors

price_history                              ← append-only, never mutated
  id, product_id, listing_id, retailer,
  price, mrp, discount_pct, in_stock, recorded_at

price_predictions                          ← ML output per product
  id, product_id, predicted_price, predicted_low, predicted_high,
  confidence, horizon_days, verdict, reasoning, model_version

watchlist_items
  id, user_id, product_id, added_at

price_alerts
  id, user_id, product_id, target_price,
  threshold_pct, retailer, is_active, triggered_at
```

---

## Scrapers

Five Playwright-based scrapers with shared stealth browser, rotating user agents, and exponential backoff retry:

| Retailer        | Product Page | Search |
|----------------|:------------:|:------:|
| Amazon.in       | ✅ | ✅ |
| Flipkart        | ✅ | ✅ |
| Myntra          | ✅ | ✅ |
| Reliance Digital| ✅ | ✅ |
| Nykaa           | ✅ | ✅ |

**Adding a new retailer:**

```python
# app/scrapers/myretailer.py
class MyRetailerScraper(BaseScraper):
    RETAILER_NAME = "MyRetailer"
    BASE_URL      = "https://www.myretailer.in"
    REQUEST_DELAY = 1.5

    async def scrape_url(self, url: str) -> ScrapedPrice: ...
    async def search_product(self, query: str, limit: int) -> list[ScrapedPrice]: ...

# app/scrapers/manager.py — add to SCRAPER_MAP:
SCRAPER_MAP["MyRetailer"] = MyRetailerScraper()
```

---

## ML Price Prediction

**Algorithm:** RandomForest + GradientBoosting ensemble trained per-product on its own price history.

**16 engineered features:**

| Feature Group | Features |
|---|---|
| Time | day_of_week, day_of_month, month, days_since_first |
| Price levels | 7d/14d/30d moving average, 7d std deviation |
| Trend | 1d/7d/30d % change |
| Position | % above all-time low, % below all-time high |
| Momentum | 3d and 7d momentum |
| Volatility | coefficient of variation |

**Verdict rules:**

| Signal | Verdict |
|---|---|
| Within 5% of all-time low + confidence ≥ 72% | BUY NOW |
| Predicted drop > 5% in 14 days | WAIT |
| Confidence < 60% | NEUTRAL |

**Minimum data:** 7 price points. Improves significantly after 30+ points.

---

## AI Price Intelligence

The `/api/v1/ai/ask` endpoint injects live product data into Claude's context — so every answer is grounded in your real scraped numbers, not generic knowledge.

**ShopSavvy mapping:**

| ShopSavvy Feature | DeltaDrop Equivalent |
|---|---|
| Deal Score | AI confidence % + BUY/WAIT verdict |
| Price History | PostgreSQL time-series → Chart.js |
| Best Time to Buy | Seasonality signals in system prompt |
| Multi-Retailer Compare | Retailer comparison block in context |
| Push Alert | APScheduler alert checker every 30 min |
| Price Prediction | RandomForest + GBR ensemble model |
| AI Recommendation | Claude claude-sonnet-4-6 with live data |

**Cost:** ~800 tokens per question. At claude-sonnet-4-6 pricing: ~$0.002/question.

---

## Scheduler Jobs

| Job | Interval | Description |
|---|---|---|
| Scrape All Listings | Every 2 hours | Update prices for all tracked products |
| ML Predictions | Every 6 hours | Re-run models for all active products |
| Check Price Alerts | Every 30 minutes | Trigger alerts when target price hit |
| Cleanup Old Data | Daily 3am IST | Delete price_history > 2 years |

Manual trigger via admin API:
```bash
curl -X POST http://localhost:8000/api/v1/admin/trigger \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"job": "scrape_all"}'
```

---

## Frontend Services

### `src/services/api.js` — Backend API client

```js
import { auth, products, watchlist, alerts, ai, formatPrice } from './services/api'

// Login
const data = await auth.login({ email, password })

// Track a product URL
await products.track('https://www.amazon.in/...', 'Amazon.in')

// Get 90-day price history for Chart.js
const history = await products.priceHistory(productId, 90)

// Ask AI
const { answer } = await ai.ask(productContext, 'Should I buy now?')
```

### `src/services/ai.js` — AI context builder

```js
import { buildProductContext, askDeltaDropAI, getSuggestedQuestions } from './services/ai'

const context = buildProductContext(product, priceHistory)
const answer  = await askDeltaDropAI(context, 'Is this the all-time low?')
```

---

## Environment Variables

### Backend `.env`

```bash
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/deltadrop
DATABASE_URL_SYNC=postgresql://postgres:password@localhost:5432/deltadrop
JWT_SECRET_KEY=your-long-random-secret-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
ANTHROPIC_API_KEY=sk-ant-api03-...
SCRAPER_HEADLESS=true
SCRAPER_CONCURRENCY=3
ADMIN_EMAIL=admin@deltadrop.in
ADMIN_PASSWORD=Admin@123!
FRONTEND_ORIGIN=http://localhost:5173
```

### Frontend `.env`

```bash
VITE_API_BASE=http://localhost:8000/api/v1
```

---

## Tests

```bash
cd deltadrop-backend
pip install pytest pytest-asyncio
pytest tests/ -v

# Results:
# tests/test_predictor.py::test_prediction_returns_dict    PASSED
# tests/test_predictor.py::test_insufficient_data_neutral  PASSED
# tests/test_predictor.py::test_verdict_is_valid           PASSED
# tests/test_predictor.py::test_predicted_price_in_bounds  PASSED
# tests/test_predictor.py::test_confidence_between_0_and_1 PASSED
# tests/test_predictor.py::test_predicted_low_below_high   PASSED
# 6 passed in 8.48s
```

---

## Production Checklist

- [ ] Change `JWT_SECRET_KEY` to a cryptographically random 64+ char string
- [ ] Set `ADMIN_PASSWORD` to something strong
- [ ] Set `SCRAPER_HEADLESS=true`
- [ ] Add Redis for caching: `REDIS_URL=redis://...`
- [ ] Run Alembic migrations instead of auto-create: `alembic upgrade head`
- [ ] Set `APP_ENV=production`
- [ ] Enable HTTPS — update `FRONTEND_ORIGIN` to your domain
- [ ] Set `ANTHROPIC_API_KEY` from https://console.anthropic.com
- [ ] Run `playwright install chromium` on server
- [ ] Configure a process manager (systemd / supervisor) for uvicorn
