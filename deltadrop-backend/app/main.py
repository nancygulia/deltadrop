import sys
import asyncio
# ── Windows Compatibility (FORCE) ──────────────────────────────────────────
# Fix Playwright/asyncio crash on Windows by using SelectorEventLoopPolicy.
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception as e:
        print(f"⚠️  [Windows] Could not set SelectorEventLoopPolicy: {e}")

"""
DeltaDrop Backend — FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager


print("\n" + "="*50)
print("DELTADROP BACKEND STARTING - CODE VERSION: DIRECT_RETAILER_V1")
print("="*50 + "\n")

from fastapi import FastAPI, Depends, HTTPException, Request

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.security import get_current_user
from app.core.errors import register_error_handlers
from app.scrapers.base import close_browser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("🚀 Starting DeltaDrop API...")
    
    # OAuth provider validation (Google Only)
    google_configured = bool(settings.GOOGLE_CLIENT_ID)
    
    if not google_configured:
        logger.warning("⚠️  Google OAuth not configured. Social login will be unavailable.")
        logger.info("💡 To configure Google OAuth: Set GOOGLE_CLIENT_ID in environment variables")
    else:
        logger.info("✅ Google OAuth is configured and ready.")

    # Create DB tables
    from app.db.session import engine, Base
    import app.models.user            # noqa — register models
    import app.models.product         # noqa — register models
    import app.models.scraper_session # noqa — register models
    import app.models.system          # noqa — register models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables ready")

    # Seed admin user
    await _seed_admin()

    # Start APScheduler
    from app.scheduler.jobs import start_scheduler
    start_scheduler()

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("🛑 Shutting down...")
    from app.scheduler.jobs import stop_scheduler
    stop_scheduler()
    await close_browser()
    from app.db.session import engine
    await engine.dispose()
    
    # Fix asyncio pipe cleanup warnings
    try:
        import asyncio
        # Cancel all remaining tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            logger.info(f"Cleaning up {len(tasks)} remaining tasks...")
            for task in tasks:
                task.cancel()
            # Wait for tasks to complete with timeout
            try:
                await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=5.0)
            except asyncio.TimeoutError:
                logger.debug("Some tasks didn't complete within timeout")
            except asyncio.CancelledError:
                # Expected during shutdown, ignore
                pass
    except Exception as e:
        logger.debug(f"Cleanup warning: {e}")
    
    logger.info("✅ Shutdown complete")


async def _seed_admin():
    from app.db.session import AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.core.security import hash_password
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        if not result.scalar_one_or_none():
            admin = User(
                email         = settings.ADMIN_EMAIL,
                username      = "admin",
                password_hash = hash_password(settings.ADMIN_PASSWORD),
                full_name     = "DeltaDrop Admin",
                role          = UserRole.admin,
                is_superuser  = True,
            )
            db.add(admin)
            await db.commit()
            logger.info(f"✅ Admin seeded: {settings.ADMIN_EMAIL}")


# ── App factory ───────────────────────────────────────────────────────────────

def _get_allowed_origins() -> list[str]:
    """Build the CORS allow-list from settings. Only the configured frontend origin
    and localhost dev servers are permitted — never wildcard."""
    origins = []
    if settings.FRONTEND_ORIGIN:
        origins.append(settings.FRONTEND_ORIGIN)
    # Always allow local dev servers
    for dev in ("http://localhost:5173", "http://127.0.0.1:5173"):
        if dev not in origins:
            origins.append(dev)
    return origins


def create_app() -> FastAPI:
    app = FastAPI(
        title       = "DeltaDrop API",
        description = "Real-time price tracking across Indian e-commerce retailers",
        version     = "1.0.0",
        docs_url    = "/docs",
        redoc_url   = "/redoc",
        lifespan    = lifespan,
    )

    # ── Standardized error handlers ───────────────────────────────────────────
    register_error_handlers(app)

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins     = _get_allowed_origins(),
        allow_credentials = True,
        allow_methods     = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers     = ["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    )

    # ── Request logging middleware (errors + security events) ─────────────────
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        response = await call_next(request)
        # Log all error responses for monitoring
        if response.status_code >= 400:
            client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            if not client_ip:
                client_ip = request.client.host if request.client else "unknown"
            logger.warning(
                f"[HTTP {response.status_code}] {request.method} {request.url.path} "
                f"from {client_ip}"
            )
        return response

    from app.api.routes.auth               import router as auth_router
    from app.api.routes.products           import router as products_router
    from app.api.routes.watchlist_alerts   import watchlist_router, alerts_router as db_alerts_router
    from app.api.routes.admin              import router as admin_router
    from app.api.routes.ai                 import router as ai_router
    from app.api.routes.admin_sessions     import router as sessions_router
    from app.api.routes.compare            import router as compare_router
    from app.api.routes import alerts           # Simple email alerts
    from app.api.routes import notifications    # In-app notifications

    PREFIX = "/api/v1"
    app.include_router(auth_router,          prefix=PREFIX)
    app.include_router(products_router,      prefix=PREFIX)
    app.include_router(watchlist_router,     prefix=PREFIX)
    app.include_router(db_alerts_router,     prefix=PREFIX)
    app.include_router(admin_router,         prefix=PREFIX)
    app.include_router(ai_router,            prefix=PREFIX)
    app.include_router(sessions_router,      prefix=PREFIX)
    app.include_router(compare_router,       prefix=PREFIX)
    app.include_router(alerts.router,        prefix=PREFIX)
    app.include_router(notifications.router, prefix=PREFIX)

    # ── Health ─────────────────────────────────────────────────────────────────
    @app.get("/api/health", tags=["Health"])
    async def health():
        from datetime import datetime, timezone
        return {
            "status":    "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version":   "1.0.0",
        }


    @app.get("/", tags=["Health"])
    async def root():
        return {"message": "DeltaDrop API · /docs for Swagger UI · /api/health for status"}

    # ── Accurate Search Endpoint ──────────────────────────────────────────────
    @app.get("/api/search", tags=["Search"])
    async def search_api(q: str):
        """
        Unified Accurate Search endpoint.
        Waits for DB persistence so every result carries a real product_id.
        Never returns a fallback/synthetic ID.
        """
        import logging as _logging
        _logger = _logging.getLogger("uvicorn")
        from urllib.parse import urlparse, parse_qs
        from app.scrapers.search_service import product_search_service
        from app.scrapers.manager import normalize_search_query

        if len(q.strip()) < 2:
            return {"query": q, "results": []}

        search_query = q.strip()
        # URL → keyword extraction
        if search_query.startswith("http://") or search_query.startswith("https://"):
            try:
                parsed = urlparse(search_query)
                parts  = [p for p in parsed.path.split('/') if p]
                extracted = ""
                host = (parsed.netloc or "").lower()
                if "amazon." in host:
                    if "dp" in parts:
                        idx = parts.index("dp")
                        extracted = " ".join(parts[:idx]).replace("-", " ")
                    elif parts:
                        extracted = parts[0].replace("-", " ")
                elif "flipkart." in host and parts:
                    extracted = parts[0].replace("-", " ")
                elif parts:
                    extracted = parts[-1].replace("-", " ").replace("_", " ")
                if len(extracted.strip()) <= 3:
                    query_params = parse_qs(parsed.query)
                    extracted = " ".join(query_params.get("q", []) + query_params.get("query", []))
                if len(extracted.strip()) > 3:
                    search_query = extracted.strip()
            except Exception:
                pass
        search_query = normalize_search_query(search_query)

        try:
            results = await product_search_service.search_products(search_query)
        except Exception as e:
            _logger.error(f"[Search] search_and_track failed: {e}")
            return {"query": q, "results": [], "error": "Search unavailable. Please try again."}

        # New search service contract: return the response payload directly.
        # Keep backward compatibility in case an older implementation returns a list.
        if isinstance(results, dict):
            results.setdefault("query", q)
            results.setdefault("retailers_scanned", len(results.get("results") or []))
            return results

        serialized = [
            {
                "selection_id": r.get("selection_id"),
                "name": r.get("name"),
                "image": r.get("image"),
                "approximate_price": r.get("approximate_price"),
                "price_range": r.get("price_range"),
                "retailer_sources": r.get("retailer_sources", []),
                "is_fallback": r.get("is_fallback", False),
                "search_mode": r.get("search_mode", "lightweight"),
                # Backward-compatible fields expected by older frontend mapping.
                "platform": (r.get("retailer_sources") or ["Unknown"])[0],
                "price": r.get("approximate_price"),
                "url": "",
                "in_stock": None,
            }
            for r in results
            if r.get("name")
        ]

        if not serialized:
            try:
                from app.scrapers.manager import scraper_manager
                fallback = await scraper_manager.search_and_track(search_query)
                fallback_rows = fallback.get("results") if isinstance(fallback, dict) else []
                serialized = [
                    {
                        "selection_id": r.get("selection_id") or r.get("product_id") or r.get("id"),
                        "name": r.get("name") or r.get("product_name"),
                        "image": r.get("image") or r.get("image_url"),
                        "approximate_price": r.get("approximate_price")
                            if r.get("approximate_price") is not None
                            else r.get("current_price"),
                        "price_range": r.get("price_range"),
                        "retailer_sources": r.get("retailer_sources") or ([r.get("retailer")] if r.get("retailer") else []),
                        "is_fallback": r.get("is_fallback", True),
                        "search_mode": r.get("search_mode", "fallback"),
                        "platform": r.get("platform") or r.get("retailer") or "Unknown",
                        "price": r.get("price") if r.get("price") is not None else r.get("current_price"),
                        "url": r.get("url") or r.get("retailer_url") or "",
                        "in_stock": r.get("in_stock"),
                    }
                    for r in fallback_rows
                    if (r.get("name") or r.get("product_name"))
                ]
                if serialized:
                    results = fallback_rows
            except Exception as e:
                _logger.warning(f"[Search] Fallback search failed: {e}")

        # Determine search mode and message
        search_modes = [r.get("search_mode", "lightweight") for r in results]
        search_sources = [r.get("search_source", "serpapi") for r in results]
        
        response = {
            "results":           serialized,
            "retailers_scanned": len(serialized),
            "query":             q,
            "search_mode":       search_modes[0] if search_modes else "none",
            "search_source":     search_sources[0] if search_sources else "none",
            "message":          None,
        }
        
        # Add helpful message based on search source
        if not serialized:
            response["message"] = "No products found. Try different keywords or check spelling."
        elif response["search_source"] == "serpapi":
            response["message"] = "Using Google Shopping search via SerpAPI."
        elif response["search_source"] == "scraperapi_enhanced":
            response["message"] = "Using enhanced ScraperAPI search across multiple retailers."
        elif response["search_source"] == "scraperapi_universal":
            response["message"] = "Using ScraperAPI with UniversalScraper fallback."
        elif response["search_source"] == "scraperapi":
            response["message"] = "Using ScraperAPI search. For Google Shopping results, configure SERPAPI_API_KEY."
        elif response["search_source"] == "basic":
            response["message"] = "Using basic search mode. Configure API keys for better results."
        
        return response


    @app.post("/api/set-alert", tags=["Search"], status_code=201)
    async def set_alert_alias(
        product_id: int,
        target_price: float,
        retailer: str = None,
        current_user = Depends(get_current_user),
    ):
        """
        Direct alias for setting price alerts.
        Fully hardened: never returns 500 — always returns valid JSON.
        """
        import logging as _logging
        _logger = _logging.getLogger("uvicorn")

        if not product_id or product_id <= 0:
            return {"success": False, "error": "Invalid product_id. Please search for the product first."}
        if not target_price or target_price <= 0:
            return {"success": False, "error": "Target price must be greater than zero."}

        try:
            from app.api.routes.watchlist_alerts import create_alert, CreateAlertRequest
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                return await create_alert(
                    body=CreateAlertRequest(
                        product_id=product_id,
                        target_price=target_price,
                        retailer=retailer,
                    ),
                    current_user=current_user,
                    db=db,
                )
        except HTTPException:
            raise  # Let 404s pass through cleanly
        except Exception as e:
            _logger.error(f"[set-alert] Unexpected error: {e}")
            return {"success": False, "error": f"Could not save alert: {str(e)}"}


    # ── Price History Endpoint ────────────────────────────────────────────────
    @app.get("/api/price-history", tags=["Search"])
    async def price_history_api(product_id: int, days: int = 90):
        """
        Returns price history for a product.

        Priority:
          1. Real rows from price_history table  (≥ 3 rows → use directly)
          2. Deterministic realistic simulation   (< 3 rows or no rows)
             – seeded from product_id so the chart is stable across page loads
             – uses PAST dates so the chart reads left-to-right as history
             – simulates Indian e-commerce patterns: gradual drift, flash sales,
               small hikes, per-retailer price offsets
        """
        import math, statistics
        from collections import defaultdict
        from datetime import datetime, timedelta, timezone

        _logger = logging.getLogger("uvicorn")

        # ── helpers ───────────────────────────────────────────────────────────

        def _sim_series(base_price: float, seed: int, n_days: int) -> list[float]:
            """
            Deterministic realistic price series for the past n_days.
            Returns one price per day, index 0 = oldest, index -1 = today.

            Patterns included:
            • Slow drift: product started ~8-18 % above current price and
              gradually fell to today's level (common in Indian e-com launches).
            • 2-4 flash-sale windows (10-28 % dip, 2-5 days each).
            • 1-2 brief price hikes (5-15 %, 3-7 days each).
            • ±1.5 % daily noise.
            All seeded deterministically so the chart is stable on reload.
            """
            import random as _rnd
            rng = _rnd.Random(seed)                    # deterministic per product

            # Start above current (products often launch higher then drop)
            start_mult = 1.0 + rng.uniform(0.08, 0.18)
            prices: list[float] = []

            # Plan events on the timeline
            events: dict[int, float] = {}              # day_idx → price multiplier

            n_sales = rng.randint(2, 4)
            for _ in range(n_sales):
                start = rng.randint(0, n_days - 6)
                dur   = rng.randint(2, 5)
                mult  = rng.uniform(0.72, 0.92)        # 8-28 % dip
                for d in range(start, min(start + dur, n_days)):
                    events[d] = min(events.get(d, 1.0), mult)  # deeper wins

            n_hikes = rng.randint(1, 2)
            for _ in range(n_hikes):
                start = rng.randint(0, n_days - 8)
                dur   = rng.randint(3, 7)
                mult  = rng.uniform(1.05, 1.15)
                for d in range(start, min(start + dur, n_days)):
                    if d not in events:                # hike only if no sale active
                        events[d] = mult

            for day_idx in range(n_days):
                progress   = day_idx / max(n_days - 1, 1)          # 0 → 1
                # Linear drift from start_mult → 1.0 (current price)
                drift_mult = start_mult + (1.0 - start_mult) * progress
                price      = base_price * drift_mult

                if day_idx in events:
                    price *= events[day_idx]

                noise  = 1.0 + rng.uniform(-0.015, 0.015)
                price *= noise

                # Clamp: never go below 55 % or above 200 % of base
                price  = max(base_price * 0.55, min(base_price * 2.0, price))
                prices.append(round(price))

            return prices

        # ── main logic ────────────────────────────────────────────────────────
        try:
            from app.db.session import AsyncSessionLocal
            from app.models.product import Product, PriceHistory
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            since = datetime.now(timezone.utc) - timedelta(days=days)

            async with AsyncSessionLocal() as db:
                product_res = await db.execute(
                    select(Product)
                    .options(selectinload(Product.retailer_listings))
                    .where(Product.id == product_id)
                )
                product = product_res.scalar_one_or_none()
                if not product:
                    return {"aggregated": [], "retailers": {}}

                active_listings = [
                    l for l in (product.retailer_listings or [])
                    if l.is_active and l.current_price is not None
                ]
                current_prices = [float(l.current_price) for l in active_listings]
                best_price     = min(current_prices) if current_prices else 0.0

                res = await db.execute(
                    select(PriceHistory)
                    .where(
                        PriceHistory.product_id == product_id,
                        PriceHistory.recorded_at >= since,
                    )
                    .order_by(PriceHistory.recorded_at)
                )
                history = res.scalars().all()

            # ── BRANCH 1: enough real data ────────────────────────────────────
            if len(history) >= 3:
                all_prices   = [float(h.price) for h in history]
                median_price = statistics.median(all_prices)
                lo, hi       = median_price * 0.5, median_price * 2.0

                retailers_map  = defaultdict(list)
                daily_prices   = defaultdict(list)

                for h in history:
                    date_str = h.recorded_at.strftime("%Y-%m-%d")
                    price    = float(h.price)
                    if lo <= price <= hi:
                        retailers_map[h.retailer.value].append({"date": date_str, "price": price})
                    daily_prices[date_str].append(price)

                aggregated_map = {}
                for date_str, day_px in daily_prices.items():
                    valid = [p for p in day_px if lo <= p <= hi]
                    aggregated_map[date_str] = min(valid) if valid else min(
                        day_px, key=lambda p: abs(p - median_price)
                    )

                return {
                    "aggregated": [
                        {"date": d, "price": p}
                        for d, p in sorted(aggregated_map.items())
                    ],
                    "retailers": dict(retailers_map),
                }

            # ── BRANCH 2: no / insufficient real data → realistic simulation ─
            # Seed is deterministic: same product always renders the same chart.
            seed = product_id * 9973 + int(best_price)

            # One simulated series per active retailer listing
            today      = datetime.now(timezone.utc).date()
            date_list  = [
                (today - timedelta(days=days - 1 - i)).isoformat()
                for i in range(days)
            ]

            retailers_map  = defaultdict(list)
            aggregated_map = {}

            if not active_listings:
                # No retailer data at all — build a single generic series
                series = _sim_series(best_price or 1000.0, seed, days)
                for date_str, price in zip(date_list, series):
                    aggregated_map[date_str] = price
            else:
                for listing in active_listings:
                    retailer_name  = listing.retailer.value
                    listing_price  = float(listing.current_price)
                    # Give each retailer its own seed offset so their lines differ
                    retailer_seed  = seed + hash(retailer_name) % 1000
                    series         = _sim_series(listing_price, retailer_seed, days)

                    for date_str, price in zip(date_list, series):
                        retailers_map[retailer_name].append({"date": date_str, "price": price})
                        # Aggregated = cheapest retailer on that day
                        if date_str not in aggregated_map or price < aggregated_map[date_str]:
                            aggregated_map[date_str] = price

            aggregated_list = [
                {"date": d, "price": p}
                for d, p in sorted(aggregated_map.items())
            ]

            _logger.info(
                f"[price_history_api] simulated {len(aggregated_list)} days "
                f"for product_id={product_id} (no real history yet)"
            )
            return {
                "aggregated":  aggregated_list,
                "retailers":   dict(retailers_map),
                "simulated":   True,
            }

        except Exception as e:
            _logger.error(f"[price_history_api] Error: {e}")
            return {"aggregated": [], "retailers": {}}

    # ── AI Recommendation Endpoint ────────────────────────────────────────────
    @app.get("/api/recommendation", tags=["Search"])
    async def recommendation_api(product_id: int):
        """
        Unified AI Recommendation endpoint.
        Fully hardened: never throws 500 — always returns a valid verdict + reasoning.
        """
        import logging as _logging
        _logger = _logging.getLogger("uvicorn")
        _logger.info(f"[recommendation_api] start product_id={product_id}")

        # Hard-coded safety net — if anything below crashes, we STILL return valid JSON
        _safe_fallback = {
            "verdict":   "WAIT",
            "reasoning": "AI Sentinel is warming up. Price analysis will be available shortly.",
            "confidence": 0,
            "method":    "safe_fallback",
            "insights": {
                "price_comparison": "Current price unavailable",
                "trend_analysis": "Trend data pending",
                "smart_recommendation": "Check back soon",
                "suggested_alert_price": None,
            },
        }

        try:
            from app.db.session import AsyncSessionLocal
            from app.models.product import Product, PriceHistory, PricePrediction
            from app.utils.ai_logic import get_ai_recommendation
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from datetime import datetime, timedelta, timezone

            async with AsyncSessionLocal() as db:
                # 1. Fetch product
                res = await db.execute(
                    select(Product)
                    .options(selectinload(Product.retailer_listings))
                    .where(Product.id == product_id)
                )
                product = res.scalar_one_or_none()
                if not product:
                    _logger.warning(f"[recommendation_api] product missing product_id={product_id}")
                    raise HTTPException(status_code=404, detail="Product not found")
                _logger.info(
                    f"[recommendation_api] product loaded product_id={product_id} "
                    f"retailer_count={len(product.retailer_listings) if product.retailer_listings else 0}"
                )

                live_prices = [
                    float(l.current_price)
                    for l in product.retailer_listings
                    if l.current_price
                ]
                seller_count = len(live_prices)
                _logger.info(
                    f"[recommendation_api] live prices collected product_id={product_id} "
                    f"seller_count={seller_count} live_prices={live_prices}"
                )

                # 2. Price history + ATL
                res = await db.execute(
                    select(PriceHistory).where(PriceHistory.product_id == product_id).order_by(PriceHistory.recorded_at)
                )
                history = res.scalars().all()
                _logger.info(f"[recommendation_api] history rows product_id={product_id} count={len(history)}")
                if not history:
                    if live_prices:
                        live_current = min(live_prices)
                        live_max = max(live_prices)
                        _logger.info(f"[recommendation_api] no history; using Gemini AI analysis product_id={product_id} current={live_current}")
                        try:
                            # Use Gemini AI for real-time analysis
                            return await asyncio.wait_for(
                                get_ai_recommendation(
                                    product.name,
                                    live_current,
                                    live_current,  # min = current when no history
                                    live_max,
                                    0.0,  # no trend when no history
                                    live_current,
                                    0.6,  # moderate confidence for AI-only analysis
                                    seller_count,
                                ),
                                timeout=30,
                            )
                        except asyncio.TimeoutError:
                            _logger.error(f"[recommendation_api] timeout on Gemini analysis product_id={product_id}")
                            return _safe_fallback
                    return _safe_fallback

                min_price  = float(min(h.price for h in history))
                max_price  = float(max(h.price for h in history))
                week_ago   = datetime.now(timezone.utc) - timedelta(days=7)
                recent     = [float(h.price) for h in history if h.recorded_at >= week_ago]
                trend      = 0.0
                if len(recent) > 1:
                    trend = ((recent[0] - recent[-1]) / (recent[-1] + 0.01)) * 100
                _logger.info(
                    f"[recommendation_api] derived metrics product_id={product_id} "
                    f"min_price={min_price} max_price={max_price} trend={trend}"
                )

                # 3. ML Prediction (best-effort)
                res = await db.execute(
                    select(PricePrediction)
                    .where(PricePrediction.product_id == product_id)
                    .order_by(PricePrediction.predicted_at.desc())
                    .limit(1)
                )
                pred = res.scalar_one_or_none()
                if pred:
                    predicted_price = float(pred.predicted_price)
                    confidence      = float(pred.confidence) if pred.confidence else 0.5
                else:
                    # Trigger async, use current as estimate for now
                    prices = live_prices
                    predicted_price = (min(prices) * 0.97) if prices else min_price
                    confidence      = 0.4
                _logger.info(
                    f"[recommendation_api] prediction snapshot product_id={product_id} "
                    f"predicted_price={predicted_price} confidence={confidence}"
                )

                # 4. Best current price
                live_prices = [
                    float(l.current_price)
                    for l in product.retailer_listings
                    if l.current_price and l.in_stock
                ]
                curr_price = min(live_prices) if live_prices else min_price
                seller_count = len([l for l in product.retailer_listings if l.current_price])
                _logger.info(
                    f"[recommendation_api] current price product_id={product_id} curr_price={curr_price} seller_count={seller_count}"
                )

                # 5. AI reasoning (internally never throws)
                try:
                    recommendation = await asyncio.wait_for(
                        get_ai_recommendation(
                            product.name,
                            curr_price,
                            min_price,
                            max_price,
                            trend,
                            predicted_price,
                            confidence,
                            seller_count,
                        ),
                        timeout=30,
                    )
                except asyncio.TimeoutError:
                    _logger.error(f"[recommendation_api] timeout on full analysis product_id={product_id}")
                    return _safe_fallback
                _logger.info(
                    f"[recommendation_api] recommendation ready product_id={product_id} "
                    f"verdict={recommendation.get('verdict')} method={recommendation.get('method')}"
                )

                return recommendation

        except HTTPException:
            raise  # Preserve 404s
        except Exception as e:
            _logger.error(f"[recommendation] Unexpected error for product {product_id}: {e}")
            return _safe_fallback

    return app


app = create_app()
