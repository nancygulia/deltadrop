# DeltaDrop Backend

Real-time price tracking across Indian e-commerce retailers — FastAPI + PostgreSQL + Playwright + ML.

## Tech Stack

| Layer          | Technology                              |
|----------------|-----------------------------------------|
| Framework      | Python 3.11 · FastAPI · Uvicorn        |
| Database       | PostgreSQL 16 · SQLAlchemy 2 (async)   |
| Migrations     | Alembic                                 |
| Scraping       | Playwright (Chromium)                   |
| ML Prediction  | scikit-learn · RandomForest + GBR      |
| Scheduling     | APScheduler (AsyncIO)                   |
| Auth           | JWT (python-jose) · bcrypt             |
| Cache          | Redis (optional)                        |

---

## Project Structure

```
deltadrop-backend/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, router registration
│   ├── core/
│   │   ├── config.py            # Settings from .env
│   │   └── security.py         # JWT + bcrypt + FastAPI deps
│   ├── db/
│   │   └── session.py           # Async SQLAlchemy engine + session
│   ├── models/
│   │   ├── user.py              # User, RefreshToken
│   │   └── product.py          # Product, RetailerListing, PriceHistory,
│   │                            # PricePrediction, WatchlistItem, PriceAlert
│   ├── api/routes/
│   │   ├── auth.py              # Register, Login, Refresh, Logout, /me
│   │   ├── products.py          # List, Track URL, Search, History, Predict
│   │   ├── watchlist_alerts.py  # Watchlist CRUD + Price Alert CRUD
│   │   └── admin.py             # Stats, trigger jobs, user management
│   ├── scrapers/
│   │   ├── base.py              # Playwright base, retry, rate limit, price parser
│   │   ├── amazon.py            # Amazon.in scraper
│   │   ├── flipkart.py          # Flipkart scraper
│   │   ├── retailers.py         # Myntra, Reliance Digital, Nykaa
│   │   └── manager.py           # Parallel orchestration, DB persistence
│   ├── ml/
│   │   ├── predictor.py         # RandomForest + GBR ensemble, BUY/WAIT verdict
│   │   └── models/              # Saved model files (.pkl)
│   ├── scheduler/
│   │   └── jobs.py              # APScheduler: scrape (2h), predict (6h), alerts (30m)
│   └── utils/
│       └── slugify.py
├── alembic/                     # DB migrations
├── scripts/
│   ├── init_db.py               # Create tables + seed admin
│   └── seed_products.py         # Seed 8 products with 90-day price history
├── tests/
│   ├── test_auth.py
│   └── test_predictor.py
├── requirements.txt
├── alembic.ini
├── pytest.ini
└── .env.example
```

---

## Setup

### 1. Prerequisites

```bash
# Python 3.11+
python --version

# PostgreSQL running
psql -U postgres -c "CREATE DATABASE deltadrop;"

# (Optional) Redis
redis-server
```

### 2. Install Dependencies

```bash
cd deltadrop-backend

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Install Playwright browser (one-time)
playwright install chromium
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env — set DATABASE_URL, JWT_SECRET_KEY
```

### 4. Initialize Database

```bash
# Create all tables + seed admin user
python scripts/init_db.py

# (Optional) Seed sample products with 90 days of price history
python scripts/seed_products.py
```

### 5. Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs
- ReDoc:      http://localhost:8000/redoc
- Health:     http://localhost:8000/api/health

---

## API Reference

### Authentication

| Method | Endpoint                    | Auth | Description              |
|--------|-----------------------------|------|--------------------------|
| POST   | /api/v1/auth/register       | ✗    | Create account           |
| POST   | /api/v1/auth/login          | ✗    | Login → JWT tokens       |
| POST   | /api/v1/auth/refresh        | ✗    | Refresh access token     |
| POST   | /api/v1/auth/logout         | ✗    | Revoke refresh token     |
| GET    | /api/v1/auth/me             | ✓    | Get current user         |
| PATCH  | /api/v1/auth/me/password    | ✓    | Change password          |

### Products

| Method | Endpoint                          | Description                        |
|--------|-----------------------------------|------------------------------------|
| GET    | /api/v1/products                  | List tracked products (paginated)  |
| POST   | /api/v1/products/track            | Add product URL to track           |
| POST   | /api/v1/products/search           | Live search across retailers       |
| GET    | /api/v1/products/{id}             | Product detail + current prices    |
| GET    | /api/v1/products/{id}/price-history | 90-day price chart data          |
| GET    | /api/v1/products/{id}/prediction  | Latest ML prediction               |
| POST   | /api/v1/products/{id}/predict     | Trigger fresh ML prediction        |

### Watchlist & Alerts

| Method | Endpoint                    | Description                   |
|--------|-----------------------------|-------------------------------|
| GET    | /api/v1/watchlist           | Get user's watchlist          |
| POST   | /api/v1/watchlist           | Add product to watchlist      |
| DELETE | /api/v1/watchlist/{id}      | Remove from watchlist         |
| GET    | /api/v1/alerts              | Get user's price alerts       |
| POST   | /api/v1/alerts              | Create price alert            |
| DELETE | /api/v1/alerts/{id}         | Delete alert                  |

### Admin

| Method | Endpoint                  | Description                    |
|--------|---------------------------|--------------------------------|
| GET    | /api/v1/admin/stats       | Platform statistics            |
| POST   | /api/v1/admin/trigger     | Manually trigger scheduler job |
| GET    | /api/v1/admin/users       | List all users                 |
| PATCH  | /api/v1/admin/users/{id}/toggle | Enable/disable user      |

---

## ML Price Prediction

The prediction engine uses a **RandomForest + GradientBoosting ensemble** trained on each product's price history.

**Features used:**
- Rolling averages (7d, 14d, 30d)
- Price trend / momentum
- Distance from all-time low / high
- Volatility (coefficient of variation)
- Day of week / month seasonality

**Verdicts:**
- `BUY_NOW` — High confidence price is at or near the floor
- `WAIT` — Price predicted to drop further in next 14 days
- `NEUTRAL` — Insufficient data or ambiguous signals

---

## Scrapers

Supported retailers with Playwright-based scrapers:

| Retailer        | Search | Product Page |
|-----------------|--------|--------------|
| Amazon.in       | ✅     | ✅           |
| Flipkart        | ✅     | ✅           |
| Myntra          | ✅     | ✅           |
| Reliance Digital| ✅     | ✅           |
| Nykaa           | ✅     | ✅           |

All scrapers use:
- Rotating user agents
- Per-retailer request delay (rate limiting)
- Exponential backoff on failure (3 retries)
- Shared Playwright browser instance

---

## Scheduler Jobs

| Job            | Frequency    | Description                           |
|----------------|--------------|---------------------------------------|
| Scrape All     | Every 2 hrs  | Update prices for all tracked products|
| ML Predictions | Every 6 hrs  | Re-run predictions for all products   |
| Check Alerts   | Every 30 min | Trigger price alerts when met         |
| Cleanup        | Daily 3am    | Remove price history > 2 years        |

---

## Frontend Integration

Add to your React `.env`:

```
VITE_API_BASE=http://localhost:8000/api/v1
```

All authenticated requests need:
```
Authorization: Bearer <access_token>
```

---

## Tests

```bash
pytest tests/ -v
```

---

## Default Admin

After `python scripts/init_db.py`:

- Email: `admin@deltadrop.in`
- Password: `Admin@123!`

Change via `/api/v1/auth/me/password` after first login.
