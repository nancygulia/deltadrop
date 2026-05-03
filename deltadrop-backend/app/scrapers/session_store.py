"""
Session Manager — cookie store for logged-in retailer scraping.

Handles:
  1. Encrypting/decrypting cookies (AES-256-GCM via cryptography library)
  2. Injecting saved cookies into Playwright browser contexts
  3. Automating login for supported retailers using Playwright
  4. Detecting when sessions expire and triggering re-login
  5. Verifying session health before each scrape

Supported login flows:
  - myntra.com     (email/password login)
  - tatacliq.com  (email/password login)
  - meesho.com    (phone + OTP — OTP via Twilio/MSG91)
  - jiomart.com   (phone + OTP — same)

Adding a new login flow = add one entry to LOGIN_FLOWS dict below.
"""
import asyncio
import json
import logging
import os
from base64 import b64encode, b64decode
from datetime import datetime, timezone, timedelta
from typing import Optional

from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)

# ── Encryption key ────────────────────────────────────────────────────────────
# Derived from the app's SECRET_KEY. 32 bytes = AES-256.
def _get_key() -> bytes:
    from app.core.config import settings
    import hashlib
    raw = (settings.SECRET_KEY or "deltadrop-dev-secret").encode()
    return hashlib.sha256(raw).digest()   # always 32 bytes


def _encrypt(plaintext: str) -> str:
    """AES-256-GCM encrypt. Returns base64-encoded ciphertext+nonce+tag."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key   = _get_key()
        nonce = os.urandom(12)   # 96-bit nonce for GCM
        ct    = AESGCM(key).encrypt(nonce, plaintext.encode(), None)
        # Pack: nonce(12) | ciphertext+tag
        return b64encode(nonce + ct).decode()
    except ImportError:
        # Fallback: no encryption (dev only — not for production)
        logger.warning("[SessionStore] cryptography not installed — cookies stored UNENCRYPTED (dev only)")
        return b64encode(plaintext.encode()).decode()


def _decrypt(ciphertext_b64: str) -> str:
    """Decrypt AES-256-GCM ciphertext."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key  = _get_key()
        raw  = b64decode(ciphertext_b64)
        nonce, ct = raw[:12], raw[12:]
        return AESGCM(key).decrypt(nonce, ct, None).decode()
    except ImportError:
        # Dev fallback
        return b64decode(ciphertext_b64).decode()


# ── Login flow definitions ─────────────────────────────────────────────────────
# Each entry: domain → login coroutine function
# Login function receives: (page, email, password, phone) → returns True/False

LOGIN_FLOWS: dict[str, str] = {
    "myntra.com":    "myntra",
    "tatacliq.com":  "tatacliq",
    "meesho.com":    "meesho",
    "jiomart.com":   "jiomart",
    "nykaa.com":     "nykaa",
    "purplle.com":   "purplle",
}

# How long cookies last per site (days)
COOKIE_TTL_DAYS: dict[str, int] = {
    "myntra.com":   30,
    "tatacliq.com": 14,
    "meesho.com":   7,
    "jiomart.com":  7,
    "nykaa.com":    30,
    "purplle.com":  30,
}


# ── Session Manager ───────────────────────────────────────────────────────────

class SessionManager:
    """
    Manages browser session cookies for retailer bot accounts.
    Singleton — one instance shared across all scrapers.
    """

    def __init__(self):
        self._cache: dict[str, list[dict]] = {}   # domain → decrypted cookies list (in-memory)
        self._lock  = asyncio.Lock()

    # ── PUBLIC: inject cookies into context ───────────────────────────────────

    async def inject_cookies(self, domain: str, ctx: BrowserContext) -> bool:
        """
        Inject stored cookies into a Playwright browser context.
        Call this BEFORE navigating to the site.

        Returns True if cookies were injected (session active).
        Returns False if no session available (scraper proceeds without login).
        """
        cookies = await self._get_cookies(domain)
        if not cookies:
            return False

        try:
            await ctx.add_cookies(cookies)
            await self._record_use(domain, success=True)
            logger.debug(f"[SessionStore] Injected {len(cookies)} cookies for {domain}")
            return True
        except Exception as e:
            logger.warning(f"[SessionStore] Cookie injection failed for {domain}: {e}")
            await self._record_use(domain, success=False)
            return False

    async def get_cookies_for_url(self, url: str) -> list[dict]:
        """Return cookies for a URL's domain, or empty list if none."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower().replace("www.", "")
        return await self._get_cookies(domain)

    # ── PUBLIC: login automation ──────────────────────────────────────────────

    async def login(
        self,
        domain:   str,
        email:    Optional[str] = None,
        password: Optional[str] = None,
        phone:    Optional[str] = None,
        otp_fn=None,           # async callable() → str (for OTP sites)
    ) -> bool:
        """
        Run the login Playwright flow for a retailer, save resulting cookies.

        Usage (from admin CLI or startup task):
          await session_manager.login(
              "myntra.com",
              email="bot@deltadrop.in",
              password="SecurePass123"
          )

        Returns True if login succeeded and cookies saved.
        """
        flow_name = LOGIN_FLOWS.get(domain)
        if not flow_name:
            logger.warning(f"[SessionStore] No login flow defined for {domain}")
            return False

        logger.info(f"[SessionStore] Starting login flow for {domain}")
        await self._update_status(domain, "logging_in")

        try:
            flow_fn = getattr(self, f"_login_{flow_name}", None)
            if not flow_fn:
                logger.error(f"[SessionStore] Login flow '_login_{flow_name}' not implemented")
                return False

            cookies = await flow_fn(
                email=email, password=password,
                phone=phone, otp_fn=otp_fn,
            )

            if cookies:
                await self._save_cookies(domain, cookies, email, phone)
                logger.info(f"[SessionStore] ✅ Login successful for {domain} — {len(cookies)} cookies saved")
                return True
            else:
                await self._update_status(domain, "failed", "Login flow returned no cookies")
                return False

        except Exception as e:
            logger.error(f"[SessionStore] Login failed for {domain}: {e}")
            await self._update_status(domain, "failed", str(e))
            return False

    async def validate_session(self, domain: str) -> bool:
        """
        Check if current session is still valid by navigating to the site
        and confirming the user appears logged in.
        Updates DB status accordingly.
        """
        cookies = await self._get_cookies(domain)
        if not cookies:
            return False

        try:
            from app.scrapers.base import get_browser
            browser = await get_browser()
            ctx     = await browser.new_context(locale="en-IN")
            await ctx.add_cookies(cookies)
            page = await ctx.new_page()

            CHECK_URLS = {
                "myntra.com":   ("https://www.myntra.com/profile", ["profile", "account", "orders"]),
                "tatacliq.com": ("https://www.tatacliq.com/my-account", ["account", "profile"]),
                "nykaa.com":    ("https://www.nykaa.com/profile", ["profile", "account"]),
                "meesho.com":   ("https://meesho.com/home", ["profile", "supply"]),
                "jiomart.com":  ("https://www.jiomart.com/my-account", ["account", "orders"]),
            }

            check_url, success_keywords = CHECK_URLS.get(
                domain, (f"https://www.{domain}", ["account", "profile", "logout"])
            )

            await page.goto(check_url, wait_until="domcontentloaded", timeout=12000)
            content = (await page.content()).lower()
            await ctx.close()

            is_valid = any(kw in content for kw in success_keywords)
            if is_valid:
                await self._update_status(domain, "active")
                logger.info(f"[SessionStore] ✅ Session valid for {domain}")
            else:
                await self._update_status(domain, "expired", "Session validation failed — not logged in")
                self._cache.pop(domain, None)
                logger.warning(f"[SessionStore] ❌ Session expired for {domain}")
            return is_valid

        except Exception as e:
            logger.warning(f"[SessionStore] Session validation error for {domain}: {e}")
            return False

    # ── LOGIN FLOWS ───────────────────────────────────────────────────────────

    async def _login_myntra(self, email: str, password: str, **_) -> Optional[list]:
        """
        Myntra email/password login.
        Flow: Home → Login → Email → Password → Submit → logged in
        """
        from app.scrapers.base import get_browser
        browser = await get_browser()
        ctx  = await browser.new_context(locale="en-IN", timezone_id="Asia/Kolkata")
        page = await ctx.new_page()
        try:
            await page.goto("https://www.myntra.com", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1500)

            # Click login button
            login_btn = await page.query_selector("a[href*='login'], [class*='login'], [data-testid='login']")
            if login_btn:
                await login_btn.click()
                await page.wait_for_timeout(1000)

            # Fill email
            email_input = await page.wait_for_selector(
                "input[type='email'], input[name='email'], input[placeholder*='email' i]",
                timeout=8000
            )
            await email_input.fill(email)

            # Click "Continue" or "Next"
            continue_btn = await page.query_selector(
                "button[type='submit'], button:has-text('Continue'), button:has-text('Next')"
            )
            if continue_btn:
                await continue_btn.click()
                await page.wait_for_timeout(1000)

            # Fill password
            pass_input = await page.wait_for_selector(
                "input[type='password']", timeout=6000
            )
            await pass_input.fill(password)

            # Submit
            submit = await page.query_selector("button[type='submit'], button:has-text('Login')")
            if submit:
                await submit.click()
                await page.wait_for_timeout(3000)

            # Verify login
            content = (await page.content()).lower()
            if "profile" in content or "orders" in content or email.lower() in content:
                cookies = await ctx.cookies()
                await ctx.close()
                return cookies

            logger.warning("[SessionStore] Myntra login: could not verify success")
            await ctx.close()
            return None

        except Exception as e:
            logger.error(f"[SessionStore] Myntra login error: {e}")
            await ctx.close()
            return None

    async def _login_tatacliq(self, email: str, password: str, **_) -> Optional[list]:
        """Tata CLiQ email/password login."""
        from app.scrapers.base import get_browser
        browser = await get_browser()
        ctx  = await browser.new_context(locale="en-IN")
        page = await ctx.new_page()
        try:
            await page.goto("https://www.tatacliq.com/login", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1500)

            await page.fill("input[type='email'], input[name='email']", email)
            await page.fill("input[type='password']", password)
            await page.click("button[type='submit'], button:has-text('Login')")
            await page.wait_for_timeout(3000)

            content = (await page.content()).lower()
            if "account" in content or "profile" in content:
                cookies = await ctx.cookies()
                await ctx.close()
                return cookies

            await ctx.close()
            return None
        except Exception as e:
            logger.error(f"[SessionStore] TataCliq login error: {e}")
            await ctx.close()
            return None

    async def _login_nykaa(self, email: str, password: str, **_) -> Optional[list]:
        """Nykaa email/password login."""
        from app.scrapers.base import get_browser
        browser = await get_browser()
        ctx  = await browser.new_context(locale="en-IN")
        page = await ctx.new_page()
        try:
            await page.goto("https://www.nykaa.com/login", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1500)

            await page.fill("input[type='email'], input[placeholder*='email' i]", email)
            await page.fill("input[type='password']", password)
            await page.click("button[type='submit'], button:has-text('Login')")
            await page.wait_for_timeout(3000)

            cookies = await ctx.cookies()
            await ctx.close()
            return cookies if cookies else None
        except Exception as e:
            logger.error(f"[SessionStore] Nykaa login error: {e}")
            await ctx.close()
            return None

    async def _login_meesho(self, phone: str, otp_fn=None, **_) -> Optional[list]:
        """
        Meesho phone + OTP login.
        otp_fn: async callable that returns the OTP string (from SMS gateway or input).
        """
        from app.scrapers.base import get_browser
        browser = await get_browser()
        ctx  = await browser.new_context(locale="en-IN")
        page = await ctx.new_page()
        try:
            await page.goto("https://meesho.com", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1500)

            # Click login
            login_btn = await page.query_selector("[class*='login'], a:has-text('Login')")
            if login_btn:
                await login_btn.click()
                await page.wait_for_timeout(1000)

            # Enter phone
            phone_input = await page.wait_for_selector(
                "input[type='tel'], input[placeholder*='phone' i], input[placeholder*='mobile' i]",
                timeout=6000
            )
            await phone_input.fill(phone)
            await page.click("button:has-text('Send OTP'), button:has-text('Get OTP')")
            await page.wait_for_timeout(2000)

            # Get OTP (from callback or wait for user input)
            if otp_fn:
                otp = await otp_fn()
            else:
                # In production: integrate Twilio/MSG91 here
                logger.warning("[SessionStore] Meesho OTP required but no otp_fn provided")
                await ctx.close()
                return None

            otp_input = await page.wait_for_selector(
                "input[placeholder*='OTP' i], input[name='otp']", timeout=10000
            )
            await otp_input.fill(otp)
            await page.click("button:has-text('Verify'), button[type='submit']")
            await page.wait_for_timeout(3000)

            cookies = await ctx.cookies()
            await ctx.close()
            return cookies if len(cookies) > 2 else None

        except Exception as e:
            logger.error(f"[SessionStore] Meesho login error: {e}")
            await ctx.close()
            return None

    async def _login_jiomart(self, phone: str, otp_fn=None, **_) -> Optional[list]:
        """JioMart phone + OTP login."""
        from app.scrapers.base import get_browser
        browser = await get_browser()
        ctx  = await browser.new_context(locale="en-IN")
        page = await ctx.new_page()
        try:
            await page.goto("https://www.jiomart.com", wait_until="domcontentloaded", timeout=15000)

            sign_in = await page.query_selector("[class*='signin'], a:has-text('Sign In')")
            if sign_in:
                await sign_in.click()
                await page.wait_for_timeout(1000)

            await page.fill("input[type='tel'], input[placeholder*='Mobile' i]", phone)
            await page.click("button:has-text('Send OTP'), button:has-text('Get OTP'), button[type='submit']")
            await page.wait_for_timeout(2000)

            if otp_fn:
                otp = await otp_fn()
                await page.fill("input[placeholder*='OTP' i]", otp)
                await page.click("button:has-text('Verify'), button[type='submit']")
                await page.wait_for_timeout(3000)
            else:
                await ctx.close()
                return None

            cookies = await ctx.cookies()
            await ctx.close()
            return cookies if len(cookies) > 2 else None

        except Exception as e:
            logger.error(f"[SessionStore] JioMart login error: {e}")
            await ctx.close()
            return None

    async def _login_purplle(self, email: str, password: str, **_) -> Optional[list]:
        """Purplle email/password login."""
        from app.scrapers.base import get_browser
        browser = await get_browser()
        ctx  = await browser.new_context(locale="en-IN")
        page = await ctx.new_page()
        try:
            await page.goto("https://www.purplle.com/login", wait_until="domcontentloaded", timeout=15000)
            await page.fill("input[type='email']", email)
            await page.fill("input[type='password']", password)
            await page.click("button[type='submit']")
            await page.wait_for_timeout(3000)
            cookies = await ctx.cookies()
            await ctx.close()
            return cookies if cookies else None
        except Exception as e:
            logger.error(f"[SessionStore] Purplle login error: {e}")
            await ctx.close()
            return None

    # ── PRIVATE: DB helpers ───────────────────────────────────────────────────

    async def _get_cookies(self, domain: str) -> list[dict]:
        """Load and decrypt cookies for domain. Uses in-memory cache."""
        # Check in-memory cache first
        if domain in self._cache:
            return self._cache[domain]

        try:
            from app.db.session import AsyncSessionLocal
            from app.models.scraper_session import ScraperSession
            from sqlalchemy import select

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ScraperSession).where(ScraperSession.domain == domain)
                )
                session = result.scalar_one_or_none()

                if not session or not session.is_active or not session.cookies_enc:
                    return []

                cookies_json = _decrypt(session.cookies_enc)
                cookies      = json.loads(cookies_json)
                self._cache[domain] = cookies
                return cookies

        except Exception as e:
            logger.debug(f"[SessionStore] Could not load cookies for {domain}: {e}")
            return []

    async def _save_cookies(
        self,
        domain:   str,
        cookies:  list,
        email:    Optional[str] = None,
        phone:    Optional[str] = None,
    ):
        """Encrypt and save cookies to DB."""
        from app.db.session import AsyncSessionLocal
        from app.models.scraper_session import ScraperSession
        from sqlalchemy import select

        cookies_json = json.dumps(cookies)
        cookies_enc  = _encrypt(cookies_json)

        ttl_days   = COOKIE_TTL_DAYS.get(domain, 14)
        now        = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=ttl_days)

        async with AsyncSessionLocal() as db:
            result  = await db.execute(
                select(ScraperSession).where(ScraperSession.domain == domain)
            )
            session = result.scalar_one_or_none()

            if session is None:
                session = ScraperSession(domain=domain)
                db.add(session)

            session.cookies_enc     = cookies_enc
            session.status          = "active"
            session.logged_in_at    = now
            session.expires_at      = expires_at
            session.last_used_at    = now
            session.login_attempts  = (session.login_attempts or 0) + 1
            if email:
                session.bot_email   = _encrypt(email)
            if phone:
                session.bot_phone   = _encrypt(phone)

            await db.commit()

        # Update cache
        self._cache[domain] = cookies
        logger.info(f"[SessionStore] Cookies saved for {domain} (expires {expires_at.date()})")

    async def _record_use(self, domain: str, success: bool):
        """Update use counters in DB."""
        try:
            from app.db.session import AsyncSessionLocal
            from app.models.scraper_session import ScraperSession
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result  = await db.execute(select(ScraperSession).where(ScraperSession.domain == domain))
                session = result.scalar_one_or_none()
                if session:
                    now = datetime.now(timezone.utc)
                    session.last_used_at = now
                    if success:
                        session.successful_uses = (session.successful_uses or 0) + 1
                    else:
                        session.failed_uses = (session.failed_uses or 0) + 1
                    await db.commit()
        except Exception:
            pass   # non-critical

    async def _update_status(self, domain: str, status: str, notes: str = ""):
        """Update session status in DB."""
        try:
            from app.db.session import AsyncSessionLocal
            from app.models.scraper_session import ScraperSession
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(ScraperSession).where(ScraperSession.domain == domain))
                session = result.scalar_one_or_none()
                if session is None:
                    session = ScraperSession(domain=domain)
                    db.add(session)
                session.status          = status
                session.last_checked_at = datetime.now(timezone.utc)
                if notes:
                    session.notes = notes
                await db.commit()
            if status in ("expired", "failed"):
                self._cache.pop(domain, None)
        except Exception as e:
            logger.debug(f"[SessionStore] Status update failed for {domain}: {e}")


# ── Singleton ─────────────────────────────────────────────────────────────────
session_manager = SessionManager()
