"""
In-app notification endpoints.
Keyed by email — works for both logged-in and anonymous users.
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.product import Notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def get_notifications(email: str, db: AsyncSession = Depends(get_db)):
    """Return recent notifications for an email address (newest first)."""
    result = await db.execute(
        select(Notification)
        .where(Notification.email == email.lower().strip())
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifs = result.scalars().all()
    unread_count = sum(1 for n in notifs if not n.is_read)
    return {
        "unread_count": unread_count,
        "notifications": [
            {
                "id":         n.id,
                "title":      n.title,
                "body":       n.body,
                "icon":       n.icon,
                "is_read":    n.is_read,
                "action_url": n.action_url,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifs
        ]
    }


@router.post("/{notification_id}/read")
async def mark_read(notification_id: int, email: str, db: AsyncSession = Depends(get_db)):
    """Mark a single notification as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id    == notification_id,
            Notification.email == email.lower().strip(),
        )
    )
    n = result.scalar_one_or_none()
    if n:
        n.is_read = True
        await db.commit()
    return {"success": True}


@router.post("/mark-all-read")
async def mark_all_read(email: str, db: AsyncSession = Depends(get_db)):
    """Mark all notifications for an email as read."""
    await db.execute(
        update(Notification)
        .where(Notification.email == email.lower().strip(), Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {"success": True}
