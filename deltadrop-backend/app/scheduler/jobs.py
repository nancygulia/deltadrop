"""
APScheduler job definitions.
Started on FastAPI app startup.
"""
import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

logger    = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")


# ── Job functions ─────────────────────────────────────────────────────────────

async def job_scrape_all():
    """Update prices by tier with different refresh intervals."""
    logger.info("[Scheduler] ⏱ Starting tiered scheduled update...")
    from app.scrapers.manager import scraper_manager
    from app.db.session import AsyncSessionLocal
    from app.models.product import Product, PriceAlert, WatchlistItem
    from sqlalchemy import select, distinct

    async with AsyncSessionLocal() as db:
        tier1 = (await db.execute(
            select(distinct(Product.name))
            .join(PriceAlert, PriceAlert.product_id == Product.id)
            .where(PriceAlert.is_active == True)
        )).scalars().all()
        tier2 = (await db.execute(
            select(distinct(Product.name))
            .join(WatchlistItem, WatchlistItem.product_id == Product.id)
            .outerjoin(PriceAlert, PriceAlert.product_id == Product.id)
            .where((PriceAlert.id == None) | (PriceAlert.is_active == False))
        )).scalars().all()

    refreshed = {"tier1": 0, "tier2": 0}
    for name in tier1:
        await scraper_manager.search_and_track(name)
        refreshed["tier1"] += 1
    if datetime.now(timezone.utc).minute % 30 == 0:
        for name in tier2:
            await scraper_manager.search_and_track(name)
            refreshed["tier2"] += 1
    logger.info(f"[Scheduler] ✅ Tiered update done: {refreshed}")


async def job_run_predictions():
    """Re-run ML predictions for all active products. Runs every 6 hours."""
    logger.info("[Scheduler] 🤖 Running ML predictions...")
    from app.db.session import AsyncSessionLocal
    from app.models.product import Product
    from app.ml.predictor import run_prediction_for_product
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result   = await db.execute(select(Product).where(Product.is_active == True))
        products = result.scalars().all()

    success = 0
    for product in products:
        try:
            async with AsyncSessionLocal() as db:
                pred = await run_prediction_for_product(product.id, db)
                if pred:
                    success += 1
        except Exception as e:
            logger.error(f"[Scheduler] Prediction failed for product {product.id}: {e}")

    logger.info(f"[Scheduler] ✅ Predictions done: {success}/{len(products)}")


async def job_cleanup_old_data():
    """Remove price history older than 2 years. Runs daily at 3am."""
    logger.info("[Scheduler] 🧹 Cleaning old price history...")
    from app.db.session import AsyncSessionLocal
    from app.models.product import PriceHistory
    from sqlalchemy import delete
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=730)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            delete(PriceHistory).where(PriceHistory.recorded_at < cutoff)
        )
        await db.commit()
    logger.info(f"[Scheduler] ✅ Cleaned {result.rowcount} old price records")


async def job_check_alerts():
    """
    Check all active price alerts against current prices.
    Runs every 5 minutes (Requirement 3).
    """
    logger.info("[Scheduler] 🔔 Checking price alerts...")
    from app.db.session import AsyncSessionLocal
    from app.models.product import PriceAlert, RetailerListing
    from app.utils.email import send_price_alert_email
    from sqlalchemy import select, update
    from sqlalchemy.orm import selectinload
    
    async with AsyncSessionLocal() as db:
        # Load user and product data eagerly
        result = await db.execute(
            select(PriceAlert)
            .options(selectinload(PriceAlert.user), selectinload(PriceAlert.product))
            .where(PriceAlert.is_active == True)
        )
        alerts = result.scalars().all()

        triggered = 0
        for alert in alerts:
            try:
                # 1. Get best current price across all retailers (or specific one if set)
                q = select(RetailerListing).where(
                    RetailerListing.product_id == alert.product_id,
                    RetailerListing.is_active  == True,
                    RetailerListing.in_stock   == True,
                    RetailerListing.current_price.isnot(None),
                )
                if alert.retailer:
                    q = q.where(RetailerListing.retailer == alert.retailer)
                    
                listings_result = await db.execute(q)
                listings   = listings_result.scalars().all()
                best_match = min(listings, key=lambda l: l.current_price, default=None) if listings else None

                if best_match and best_match.current_price <= alert.target_price:
                    logger.info(f"[Scheduler] ✨ Alert {alert.id} hit for {alert.user.email}! ₹{best_match.current_price} <= ₹{alert.target_price}")
                    alert.is_active = False
                    alert.triggered_at = datetime.now(timezone.utc)
                    await db.flush()
                    await db.commit()

                    await asyncio.to_thread(
                        send_price_alert_email,
                        to_email=alert.user.email,
                        name=alert.user.full_name or alert.user.username,
                        product_name=alert.product.name,
                        current_price=float(best_match.current_price),
                        target_price=float(alert.target_price),
                        product_url=best_match.retailer_url,
                    )
                    triggered += 1
            except Exception as e:
                await db.rollback()
                logger.error(f"[Scheduler] Alert {alert.id} processing failed: {e}")
                # Continue processing other alerts instead of failing the entire batch

    logger.info(f"[Scheduler] ✅ Alert check done: {triggered} triggered")


async def job_check_simple_alerts():
    """
    Check all active SimpleWatchlistAlerts (email-only, no login required).
    Calls compare_prices for each tracked product, sends email + saves
    Notification row when price <= target_price.
    Runs every 10 minutes.
    """
    logger.info("[Scheduler] 🔔 Checking simple watchlist alerts...")
    from app.db.session import AsyncSessionLocal
    from app.models.product import SimpleWatchlistAlert, Notification
    from app.scrapers.product_engine import compare_prices
    from app.services.email_service import send_email
    from sqlalchemy import select
    from decimal import Decimal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SimpleWatchlistAlert).where(SimpleWatchlistAlert.is_active == True)
        )
        alerts = result.scalars().all()

    triggered = 0
    for alert in alerts:
        try:
            data = await compare_prices(alert.product_name)
            best_price = data.get("best_price")
            if best_price is None:
                continue

            best_price_dec = Decimal(str(best_price))

            async with AsyncSessionLocal() as db:
                # Refresh alert within this session
                res   = await db.execute(select(SimpleWatchlistAlert).where(SimpleWatchlistAlert.id == alert.id))
                a     = res.scalar_one_or_none()
                if not a or not a.is_active:
                    continue

                a.last_price = best_price_dec  # always update cached price

                if best_price_dec <= a.target_price:
                    logger.info(
                        f"[Scheduler] ✨ Simple alert triggered: {a.product_name} "
                        f"₹{best_price} <= ₹{a.target_price} → {a.email}"
                    )
                    a.is_active    = False
                    a.triggered_at = datetime.now(timezone.utc)

                    # Build email body
                    subject = f"🔔 Price Drop Alert: {a.product_name}"
                    body = (
                        f"Hi there!\n\n"
                        f"Great news — the price dropped for:\n\n"
                        f"  📦 {a.product_name}\n"
                        f"  💰 Now: ₹{best_price:,.0f}  (your target: ₹{float(a.target_price):,.0f})\n"
                        + (f"  🔗 {data.get('best_store_url', '')}\n" if data.get("best_store_url") else "")
                        + f"\nThis alert has been deactivated. Set a new one any time.\n\n"
                        f"— DeltaDrop"
                    )

                    # Save in-app notification
                    notif = Notification(
                        email      = a.email,
                        title      = f"Price Drop: {a.product_name}",
                        body       = f"Now ₹{best_price:,.0f} — your target was ₹{float(a.target_price):,.0f}",
                        icon       = "🔔",
                        action_url = data.get("best_store_url") or f"/product?q={a.product_name}",
                    )
                    db.add(notif)
                    await db.commit()

                    # Send email (non-blocking)
                    await asyncio.to_thread(send_email, a.email, subject, body)
                    triggered += 1
                else:
                    await db.commit()  # persist last_price update

        except Exception as e:
            logger.error(f"[Scheduler] Simple alert {alert.id} failed: {e}")

    logger.info(f"[Scheduler] ✅ Simple alert check done: {triggered} triggered")


# ── Scheduler lifecycle ───────────────────────────────────────────────────────

def _on_job_event(event):
    if event.exception:
        logger.error(f"[Scheduler] ❌ Job {event.job_id} failed: {event.exception}")
    else:
        logger.debug(f"[Scheduler] ✓ Job {event.job_id} completed")


def start_scheduler():
    scheduler.add_listener(_on_job_event, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

    # Update prices via SerpAPI every 30 minutes
    scheduler.add_job(
        job_scrape_all,
        trigger="interval", minutes=30, id="scrape_all",
        name="SerpAPI Alerted Products Update", replace_existing=True,
    )

    # ML predictions every 6 hours
    scheduler.add_job(
        job_run_predictions,
        trigger="interval", hours=6, id="predictions",
        name="ML Price Predictions", replace_existing=True,
    )

    # Price alert check every 5 minutes (vibrant/near-real-time)
    scheduler.add_job(
        job_check_alerts,
        trigger="interval", minutes=5, id="alerts",
        name="Check Price Alerts", replace_existing=True,
    )

    # Simple (email-only) watchlist alert check every 10 minutes
    scheduler.add_job(
        job_check_simple_alerts,
        trigger="interval", minutes=10, id="simple_alerts",
        name="Check Simple Watchlist Alerts", replace_existing=True,
    )

    # Cleanup old data daily at 3am IST
    scheduler.add_job(
        job_cleanup_old_data,
        trigger="cron", hour=3, minute=0, id="cleanup",
        name="Cleanup Old Data", replace_existing=True,
    )

    scheduler.start()
    logger.info("✅ APScheduler started with 5 jobs")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")

