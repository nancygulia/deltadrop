"""
Simple email-only price alerts (no login required).
Backed by DB via SimpleWatchlistAlert model.
"""
import logging
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.product import SimpleWatchlistAlert

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["Simple Email Alerts"])


class AlertRequest(BaseModel):
    email:        EmailStr
    product:      str
    target_price: float


@router.post("")
async def create_alert(alert: AlertRequest, db: AsyncSession = Depends(get_db)):
    """
    Creates a DB-persisted email price alert (no auth required).
    Idempotent: updates target_price if same email+product already exists.
    """
    product_name = alert.product.strip()
    email        = alert.email.lower().strip()

    # Check for existing active alert for same email + product
    result = await db.execute(
        select(SimpleWatchlistAlert).where(
            SimpleWatchlistAlert.email        == email,
            SimpleWatchlistAlert.product_name == product_name,
            SimpleWatchlistAlert.is_active    == True,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.target_price = Decimal(str(alert.target_price))
        await db.commit()
        logger.info(f"[Alerts] Updated simple alert for {email} on '{product_name}' → ₹{alert.target_price}")
        return {"success": True, "message": "Alert updated successfully"}

    new_alert = SimpleWatchlistAlert(
        email        = email,
        product_name = product_name,
        target_price = Decimal(str(alert.target_price)),
        is_active    = True,
    )
    db.add(new_alert)
    await db.commit()
    logger.info(f"[Alerts] Created simple alert for {email} on '{product_name}' → ₹{alert.target_price}")
    return {"success": True, "message": "Alert set successfully"}


@router.get("")
async def list_alerts(email: str, db: AsyncSession = Depends(get_db)):
    """List all active alerts for a given email (no auth required)."""
    result = await db.execute(
        select(SimpleWatchlistAlert)
        .where(
            SimpleWatchlistAlert.email     == email.lower().strip(),
            SimpleWatchlistAlert.is_active == True,
        )
        .order_by(SimpleWatchlistAlert.created_at.desc())
    )
    alerts = result.scalars().all()
    return {
        "alerts": [
            {
                "id":           a.id,
                "product_name": a.product_name,
                "target_price": float(a.target_price),
                "last_price":   float(a.last_price) if a.last_price else None,
                "created_at":   a.created_at.isoformat(),
            }
            for a in alerts
        ]
    }


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, email: str, db: AsyncSession = Depends(get_db)):
    """Deactivate a specific alert (email is used as ownership check)."""
    result = await db.execute(
        select(SimpleWatchlistAlert).where(
            SimpleWatchlistAlert.id    == alert_id,
            SimpleWatchlistAlert.email == email.lower().strip(),
        )
    )
    a = result.scalar_one_or_none()
    if not a:
        return {"success": False, "error": "Alert not found"}
    a.is_active = False
    await db.commit()
    return {"success": True, "message": "Alert removed"}
