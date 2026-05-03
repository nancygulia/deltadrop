"""
Admin API — Session Store management endpoints.

Only accessible by admin users (is_superuser = True).
Lets you trigger logins, check session health, and revoke sessions
without touching the database directly.

Routes:
  GET  /admin/sessions          → list all session statuses
  POST /admin/sessions/login    → run login flow for a retailer
  POST /admin/sessions/validate → re-validate all active sessions
  DELETE /admin/sessions/{domain} → revoke / clear a session
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/admin/sessions", tags=["Admin — Sessions"])


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ── Schemas ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    domain:   str            # e.g. "myntra.com"
    email:    Optional[str] = None
    password: Optional[str] = None
    phone:    Optional[str] = None
    otp:      Optional[str] = None   # for OTP sites: provide OTP manually


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("")
async def list_sessions(_: User = Depends(_require_admin)):
    """List all retailer sessions and their status."""
    from app.db.session import AsyncSessionLocal
    from app.models.scraper_session import ScraperSession
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result   = await db.execute(select(ScraperSession))
        sessions = result.scalars().all()

    now = datetime.now(timezone.utc)
    return {
        "sessions": [
            {
                "domain":          s.domain,
                "status":          s.status,
                "is_active":       s.is_active,
                "logged_in_at":    s.logged_in_at.isoformat() if s.logged_in_at else None,
                "expires_at":      s.expires_at.isoformat()   if s.expires_at   else None,
                "expires_in_days": (s.expires_at - now).days  if s.expires_at and s.expires_at > now else None,
                "last_used_at":    s.last_used_at.isoformat()  if s.last_used_at  else None,
                "successful_uses": s.successful_uses,
                "failed_uses":     s.failed_uses,
                "login_attempts":  s.login_attempts,
                "notes":           s.notes,
            }
            for s in sessions
        ]
    }


@router.post("/login")
async def trigger_login(
    body: LoginRequest,
    _: User = Depends(_require_admin),
):
    """
    Run the login Playwright flow for a retailer and save the session cookies.

    For email/password sites (Myntra, TataCliq, Nykaa):
      POST { "domain": "myntra.com", "email": "bot@...", "password": "..." }

    For OTP sites (Meesho, JioMart):
      Step 1: POST { "domain": "meesho.com", "phone": "+919876543210" }
              → Returns { "otp_required": true }
      Step 2: POST { "domain": "meesho.com", "phone": "+919876543210", "otp": "123456" }
              → Returns { "success": true }
    """
    from app.scrapers.session_store import session_manager

    # OTP flow: if OTP provided, create a one-shot otp_fn
    otp_fn = None
    if body.otp:
        captured_otp = body.otp
        async def _otp_fn():
            return captured_otp
        otp_fn = _otp_fn

    success = await session_manager.login(
        domain=body.domain,
        email=body.email,
        password=body.password,
        phone=body.phone,
        otp_fn=otp_fn,
    )

    if success:
        return {"success": True, "domain": body.domain, "message": "Session saved — scraper is now logged in"}
    else:
        # Check if OTP is needed
        from app.scrapers.session_store import LOGIN_FLOWS
        flow = LOGIN_FLOWS.get(body.domain, "")
        needs_otp = flow in ("meesho", "jiomart") and not body.otp
        if needs_otp:
            return {
                "success": False,
                "otp_required": True,
                "message": f"OTP sent to {body.phone}. Re-submit request with otp field.",
            }
        raise HTTPException(status_code=400, detail=f"Login failed for {body.domain} — check credentials or site UI changed")


@router.post("/validate")
async def validate_all_sessions(_: User = Depends(_require_admin)):
    """
    Re-validate all active sessions by navigating to each site
    and confirming the bot is still logged in.
    Updates status to 'expired' if session is stale.
    """
    from app.scrapers.session_store import session_manager
    from app.db.session import AsyncSessionLocal
    from app.models.scraper_session import ScraperSession
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result   = await db.execute(
            select(ScraperSession).where(ScraperSession.status == "active")
        )
        sessions = result.scalars().all()

    results = {}
    for s in sessions:
        valid = await session_manager.validate_session(s.domain)
        results[s.domain] = "valid" if valid else "expired"

    return {"validated": results}


@router.delete("/{domain}")
async def revoke_session(domain: str, _: User = Depends(_require_admin)):
    """Revoke a session — scraper will stop using cookies for this retailer."""
    from app.db.session import AsyncSessionLocal
    from app.models.scraper_session import ScraperSession
    from sqlalchemy import select
    from app.scrapers.session_store import session_manager

    async with AsyncSessionLocal() as db:
        result  = await db.execute(select(ScraperSession).where(ScraperSession.domain == domain))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail=f"No session found for {domain}")
        session.status      = "disabled"
        session.cookies_enc = None
        await db.commit()

    session_manager._cache.pop(domain, None)
    return {"success": True, "message": f"Session for {domain} revoked"}
