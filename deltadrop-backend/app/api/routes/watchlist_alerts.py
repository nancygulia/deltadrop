"""Watchlist and Price Alert routes."""
import logging
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.product import WatchlistItem, PriceAlert, Product

# ── Watchlist ──────────────────────────────────────────────────────────────────
watchlist_router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


class WatchlistAddRequest(BaseModel):
    product_id: int


@watchlist_router.get("")
async def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    result = await db.execute(
        select(WatchlistItem)
        .options(selectinload(WatchlistItem.product).selectinload(Product.retailer_listings))
        .where(WatchlistItem.user_id == current_user.id)
        .order_by(WatchlistItem.added_at.desc())
    )
    items = result.scalars().all()
    return {
        "data": [
            {
                "id":        item.id,
                "added_at":  item.added_at.isoformat(),
                "product": {
                    "id":       item.product.id,
                    "name":     item.product.name,
                    "slug":     item.product.slug,
                    "category": item.product.category.value,
                    "image_url":item.product.image_url,
                    "best_price": float(min(
                        (l.current_price for l in item.product.retailer_listings if l.current_price and l.in_stock),
                        default=0
                    )) or None,
                }
            }
            for item in items
        ]
    }


@watchlist_router.post("", status_code=201)
async def add_to_watchlist(
    body: WatchlistAddRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    # Check product exists
    result  = await db.execute(select(Product).where(Product.id == body.product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check already in watchlist
    result  = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id    == current_user.id,
            WatchlistItem.product_id == body.product_id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already in watchlist")

    item = WatchlistItem(user_id=current_user.id, product_id=body.product_id)
    db.add(item)
    await db.commit()
    return {"success": True, "message": f"Added {product.name} to watchlist"}


@watchlist_router.delete("/{product_id}")
async def remove_from_watchlist(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id    == current_user.id,
            WatchlistItem.product_id == product_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not in watchlist")

    await db.delete(item)
    await db.commit()
    return {"success": True, "message": "Removed from watchlist"}


# ── Price Alerts ───────────────────────────────────────────────────────────────
alerts_router = APIRouter(prefix="/alerts", tags=["Price Alerts"])


class CreateAlertRequest(BaseModel):
    product_id:    int
    target_price:  float
    threshold_pct: Optional[float] = None
    retailer:      Optional[str]   = None


@alerts_router.get("")
async def get_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    result = await db.execute(
        select(PriceAlert)
        .options(selectinload(PriceAlert.product))
        .where(PriceAlert.user_id == current_user.id)
        .order_by(PriceAlert.created_at.desc())
    )
    alerts = result.scalars().all()
    return {
        "data": [
            {
                "id":           a.id,
                "target_price": float(a.target_price),
                "threshold_pct":float(a.threshold_pct) if a.threshold_pct else None,
                "retailer":     a.retailer,
                "is_active":    a.is_active,
                "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
                "created_at":   a.created_at.isoformat(),
                "product": {
                    "id":       a.product.id,
                    "name":     a.product.name,
                    "image_url":a.product.image_url,
                },
            }
            for a in alerts
        ]
    }


@alerts_router.post("", status_code=201)
@alerts_router.post("/set-alert", status_code=201)
async def create_alert(
    body: CreateAlertRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    """
    Fixed Bug 1: Added proper validation + try/catch to avoid 500 errors.
    """
    try:
        # 1. Validation: Ensure product exists
        result  = await db.execute(select(Product).where(Product.id == body.product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # 2. Validation: Basic price check
        if body.target_price <= 0:
            raise HTTPException(status_code=400, detail="Target price must be greater than zero")

        # 3. Create Alert
        alert = PriceAlert(
            user_id       = current_user.id,
            product_id    = body.product_id,
            target_price  = Decimal(str(body.target_price)),
            threshold_pct = Decimal(str(body.threshold_pct)) if body.threshold_pct else None,
            retailer      = body.retailer,
            is_active     = True
        )
        db.add(alert)
        await db.commit()
        
        return {
            "success": True, 
            "message": f"Alert activated! We will notify you when {product.name} hits ₹{body.target_price:,.0f}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Alerts] Failed to set alert: {e}")
        return {"success": False, "error": f"Failed to save alert: {str(e)}"}


@alerts_router.delete("/{alert_id}")
async def delete_alert(
    alert_id:   int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    result = await db.execute(
        select(PriceAlert).where(PriceAlert.id == alert_id, PriceAlert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.delete(alert)
    await db.commit()
    return {"success": True, "message": "Alert deleted"}
@alerts_router.patch("/{alert_id}/toggle")
async def toggle_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    result = await db.execute(
        select(PriceAlert).where(PriceAlert.id == alert_id, PriceAlert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_active = not alert.is_active
    await db.commit()
    return {"success": True, "is_active": alert.is_active, "message": f"Alert {'activated' if alert.is_active else 'deactivated'}"}
