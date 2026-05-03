"""Admin-only routes: manual scrape triggers, stats, user management."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_admin
from app.db.session import get_db
from app.models.user import User
from app.models.product import Product, PriceHistory, RetailerListing, PriceAlert

router = APIRouter(prefix="/admin", tags=["Admin"])

from app.models.system import RateLimitState

# Rate-limit tracker for manual scrape triggers (seconds)
RATE_LIMIT_SECONDS = 120


class TriggerRequest(BaseModel):
    job: str  # "scrape_all" | "predictions" | "alerts" | "cleanup"


@router.post("/trigger")
async def trigger_job(
    body: TriggerRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession   = Depends(get_db),
):
    VALID_JOBS = {"scrape_all", "predictions", "alerts", "cleanup"}
    if body.job not in VALID_JOBS:
        raise HTTPException(status_code=400, detail=f"Unknown job. Valid: {VALID_JOBS}")

    limit_key = f"admin:job:{body.job}"
    
    # Check persistent rate limit
    result = await db.execute(select(RateLimitState).where(RateLimitState.key == limit_key))
    state  = result.scalar_one_or_none()
    
    now = datetime.now(timezone.utc)
    if state:
        elapsed = (now - state.last_triggered).total_seconds()
        if elapsed < RATE_LIMIT_SECONDS:
            wait = int(RATE_LIMIT_SECONDS - elapsed)
            raise HTTPException(status_code=429, detail=f"Rate limited. Retry in {wait}s")
        
        state.last_triggered = now
        state.hits += 1
    else:
        db.add(RateLimitState(key=limit_key, last_triggered=now))

    await db.commit()

    import asyncio
    from app.scheduler.jobs import (
        job_scrape_all, job_run_predictions,
        job_check_alerts, job_cleanup_old_data,
    )

    job_map = {
        "scrape_all":  job_scrape_all,
        "predictions": job_run_predictions,
        "alerts":      job_check_alerts,
        "cleanup":     job_cleanup_old_data,
    }

    try:
        asyncio.create_task(job_map[body.job]())
        return {"success": True, "job": body.job, "queued": True, "started_at": now.isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats(
    db: AsyncSession    = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    total_products  = (await db.execute(select(func.count(Product.id)))).scalar()
    total_users     = (await db.execute(select(func.count(User.id)))).scalar()
    total_history   = (await db.execute(select(func.count(PriceHistory.id)))).scalar()
    active_listings = (await db.execute(
        select(func.count(RetailerListing.id)).where(RetailerListing.is_active == True)
    )).scalar()
    active_alerts   = (await db.execute(
        select(func.count(PriceAlert.id)).where(PriceAlert.is_active == True)
    )).scalar()

    return {
        "total_products":  total_products,
        "total_users":     total_users,
        "total_price_records": total_history,
        "active_listings": active_listings,
        "active_alerts":   active_alerts,
        "timestamp":       datetime.now(timezone.utc).isoformat(),
    }


@router.get("/users")
async def list_users(
    db: AsyncSession    = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users  = result.scalars().all()
    return {
        "data": [
            {
                "id":         u.id,
                "email":      u.email,
                "username":   u.username,
                "role":       u.role.value,
                "is_active":  u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ]
    }


@router.patch("/users/{user_id}/toggle")
async def toggle_user(
    user_id: int,
    db: AsyncSession    = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = not user.is_active
    await db.commit()
    return {"success": True, "user_id": user_id, "is_active": user.is_active}
