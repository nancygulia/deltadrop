"""
ScraperSession — stores encrypted browser cookies for bot accounts.

One row per retailer domain. Playwright loads these cookies before scraping
so DeltaDrop scrapes as a "logged-in" user and sees member prices,
personalised offers, and avoids login prompts.

Cookie data is AES-256-GCM encrypted at rest using the app secret key.
Even if the DB is compromised, cookies cannot be used without the key.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ScraperSession(Base):
    """
    Encrypted cookie store for one retailer bot account.

    Lifecycle:
      1. Admin runs: session_manager.login("myntra.com")
         → Playwright opens Myntra → fills credentials → OTP flow → logged in
         → Cookies saved here (encrypted)
      2. Every scrape fetch: load cookies → inject into Playwright context
         → scraper sees logged-in page → member prices visible
      3. Cookies expire or session invalidated → status="expired"
         → Next scrape triggers auto re-login
    """
    __tablename__ = "scraper_sessions"

    id              : Mapped[int]           = mapped_column(primary_key=True)
    domain          : Mapped[str]           = mapped_column(String(200), nullable=False, unique=True, index=True)
    # e.g. "myntra.com", "tatacliq.com", "jiomart.com", "meesho.com"

    # Bot account credentials (encrypted)
    bot_email       : Mapped[Optional[str]] = mapped_column(String(500))  # AES encrypted
    bot_phone       : Mapped[Optional[str]] = mapped_column(String(200))  # AES encrypted

    # Cookie data — full Playwright cookies list as JSON, AES-256-GCM encrypted
    cookies_enc     : Mapped[Optional[str]] = mapped_column(Text)

    # Session health
    status          : Mapped[str]           = mapped_column(String(50), default="pending")
    # "pending"  → never logged in
    # "active"   → cookies valid, injected in scrapes
    # "expired"  → cookies stale, re-login needed
    # "failed"   → login automation failed (wrong creds / changed UI)
    # "disabled" → manually disabled

    # Timing
    logged_in_at    : Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at      : Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_used_at    : Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_checked_at : Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Stats
    successful_uses : Mapped[int]           = mapped_column(Integer, default=0)
    failed_uses     : Mapped[int]           = mapped_column(Integer, default=0)
    login_attempts  : Mapped[int]           = mapped_column(Integer, default=0)

    # Notes (e.g. "OTP missing", "site UI changed")
    notes           : Mapped[Optional[str]] = mapped_column(Text)

    created_at      : Mapped[datetime]      = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at      : Mapped[datetime]      = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_scraper_sessions_status", "status"),
    )

    @property
    def is_active(self) -> bool:
        if self.status != "active":
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    def __repr__(self):
        return f"<ScraperSession {self.domain} [{self.status}]>"
