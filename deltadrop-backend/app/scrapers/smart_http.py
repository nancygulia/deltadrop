"""
Smart HTTP Engine — universal waterfall for all retailers, all input types.

Every retailer gets its OPTIMAL method first based on site_profiles.py,
then falls back intelligently. Playwright is the GUARANTEED last resort —
meaning NO retailer ever disappears from results due to blocking.

Per-site order (from site_profiles.py tier):
  amazon.in    → urllib    → curl_cffi → httpx → playwright
  flipkart.com → curl_cffi → httpx     → urllib → playwright
  ajio.com     → httpx     → curl_cffi → urllib → playwright
  meesho.com   → playwright (directly — known JS-heavy site)
  any site     → urllib    → curl_cffi → httpx  → playwright (default)

Every fetch returns:
  (html, method_used, fetch_time_ms)

This applies uniformly to ALL input types:
  URL scraping   → fetch_for_url(url)
  Name search    → fetch_for_search(search_url, profile)
  Image search   → (image → name → same as name search above)
"""
import asyncio
import logging
import time
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# ScraperAPI concurrency limit (Trial = 5)
_scraperapi_semaphore = asyncio.Semaphore(5)

<<<<<<< HEAD
# Scrape.do concurrency limit
_scrapedo_semaphore = asyncio.Semaphore(5)

=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
# ── Tier → waterfall order ────────────────────────────────────────────────────
# For each site tier, defines the ORDER of HTTP methods to try.
# First = preferred (fastest/least blocked). Last = guaranteed fallback.

WATERFALL_ORDER: dict[str, list[str]] = {
    "urllib":     ["urllib",    "curl_cffi", "httpx",     "playwright"],
    "curl_cffi":  ["curl_cffi", "httpx",     "urllib",    "playwright"],
    "httpx":      ["httpx",     "curl_cffi", "urllib",    "playwright"],
    "playwright": ["playwright"],   # JS-heavy sites — go straight to Playwright
    "shopify":    ["urllib",    "curl_cffi", "httpx",     "playwright"],  # API endpoint, usually open
    "woocommerce":["urllib",    "curl_cffi", "httpx",     "playwright"],
}

# ── Block detection patterns ──────────────────────────────────────────────────
# If fetched HTML contains any of these, it's a block page — try next method.
BLOCK_SIGNATURES = [
    "captcha",
    "access denied",
    "robot check",
    "cloudflare",
    "please enable javascript",
    "enable cookies",
    "security check",
    "verify you are human",
    "unusual traffic",
    "403 forbidden",
    "service unavailable",
    "too many requests",
    "rate limit",
    "<title>429",
    "<title>403",
    "<title>503",
    "ddos-guard",
    "suspicious activity",
    "pardon our interruption",
    "unusual traffic",
    "detecting unusual traffic",
    "robot.txt",
    "our systems have detected",
    "one more step",        # Another Cloudflare variant
    "automated access",
    "request was blocked",
    "suspicious activity",
    "pardon our interruption",
]

# JS-price signals: these in HTML mean price is loaded via JavaScript
# If we see these AND no price digits → page needs Playwright
JS_PRICE_SIGNALS = [
    "__next_data__",        # Next.js — Myntra, Meesho
    "window.__initial_state__",
    "react-root",
    "ng-app",               # Angular (some sites)
    "__nuxt__",             # Nuxt.js
    "data-react-helmet",
]

MIN_REAL_HTML_BYTES = 1000

# ── India price pattern ───────────────────────────────────────────────────────
import re as _re
_PRICE_PATTERN = _re.compile(r'(?:₹|rs\.?\s*|inr\s*)[\s]*[\d,]{3,}', _re.IGNORECASE)
_NUMERIC_PRICE = _re.compile(r'"price"\s*:\s*"?(\d{3,})"?')


def _is_blocked(html: str) -> bool:
    """Return True if HTML is a CAPTCHA/block page, not a real product page."""
    if not html or len(html) < MIN_REAL_HTML_BYTES:
        return True
    hl = html[:3000].lower()
    return any(sig in hl for sig in BLOCK_SIGNATURES)


def _has_price_signal(html: str) -> bool:
    """
    Return True if the HTML likely contains a real price.
    Prevents declaring a JS-skeleton page as 'successful' when price is missing.
    Only used for pages that passed _is_blocked() check.
    """
    if not html:
        return False
    # Fast check: any rupee pattern or JSON price in the HTML
    sample = html[:50000]  # first 50KB is enough
    if _PRICE_PATTERN.search(sample):
        return True
    if _NUMERIC_PRICE.search(sample):
        return True
    return False


def _is_js_rendered_site(html: str) -> bool:
    """
    Return True if the page is a JS-heavy SPA where prices are rendered client-side.
    In this case, even a 'successful' HTTP fetch won't have the price in the HTML.
    """
    hl = html[:5000].lower()
    return any(sig in hl for sig in JS_PRICE_SIGNALS)



# ── Individual HTTP fetch functions ──────────────────────────────────────────

def _fetch_urllib(url: str, timeout: int = 12) -> Optional[str]:
    """Plain urllib — fastest, no extra deps, works for ~60% of Indian retail sites."""
    import urllib.request
    import urllib.error
    import random
    import gzip

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    ]
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent":      random.choice(USER_AGENTS),
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT":             "1",
            "Connection":      "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if resp.info().get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return raw.decode("utf-8", errors="replace")
    except Exception:
        return None


def _fetch_curl_cffi(url: str, timeout: int = 12) -> Optional[str]:
    """
    curl_cffi — Chrome TLS fingerprint impersonation.
    Bypasses Cloudflare and TLS-based bot detection.
    Required for: Flipkart, Nykaa, Nike, Adidas, and Cloudflare-protected sites.
    """
    try:
        from curl_cffi import requests as cffi_requests
        resp = cffi_requests.get(
            url,
            impersonate="chrome124",
            timeout=timeout,
            headers={
                "Accept-Language": "en-IN,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        if resp.status_code < 400:
            return resp.text
        return None
    except ImportError:
        logger.warning("[SmartHTTP] curl_cffi not installed — skipping")
        return None
    except Exception:
        return None


def _fetch_httpx(url: str, timeout: int = 12) -> Optional[str]:
    """
    httpx — HTTP/2 support.
    Works for sites that require HTTP/2: Ajio, some brand sites.
    """
    try:
        import httpx
<<<<<<< HEAD
        logger.debug("[SmartHTTP] httpx import successful")
=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
        headers = {
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
        }
        with httpx.Client(http2=True, follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code < 400:
                return resp.text
        return None
<<<<<<< HEAD
    except ImportError as e:
        logger.warning(f"[SmartHTTP] httpx import failed: {e} — skipping")
        return None
    except Exception as e:
        logger.warning(f"[SmartHTTP] httpx fetch failed: {e} — skipping")
=======
    except ImportError:
        logger.warning("[SmartHTTP] httpx not installed — skipping")
        return None
    except Exception:
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
        return None


async def _fetch_scraperapi(url: str, timeout: int = 15) -> Optional[str]:
    """
    Professional Scraping API (scraperapi.com).
    Bypasses EVERYTHING: Cloudflare, CAPTCHAs, IP bans, and browser fingerprinting.
    Uses residential proxies tailored for the target retailer.
    """
    if not settings.SCRAPER_API_KEY:
        return None

    async with _scraperapi_semaphore:
        try:
            import urllib.parse
            import urllib.request
            import concurrent.futures

            encoded_url = urllib.parse.quote_plus(url)
<<<<<<< HEAD
            api_url = f"https://api.scraperapi.com?api_key={settings.SCRAPER_API_KEY}&url={encoded_url}&render_js=true&premium=true&country_code=in"
=======
            api_url = f"http://api.scraperapi.com?api_key={settings.SCRAPER_API_KEY}&url={encoded_url}"
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
            
            loop = asyncio.get_event_loop()
            
            def _sync_fetch():
                req = urllib.request.Request(api_url)
<<<<<<< HEAD
                req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
                req.add_header('Accept-Language', 'en-US,en;q=0.5')
                req.add_header('Accept-Encoding', 'gzip, deflate')
                req.add_header('DNT', '1')
                req.add_header('Connection', 'keep-alive')
                req.add_header('Upgrade-Insecure-Requests', '1')
                req.add_header('Sec-Fetch-Dest', 'document')
                req.add_header('Sec-Fetch-Mode', 'navigate')
                req.add_header('Sec-Fetch-Site', 'none')
                req.add_header('Cache-Control', 'max-age=0')
=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.read().decode("utf-8", errors="replace")

            # Run synchronous urllib in a thread pool to avoid blocking the event loop
            return await loop.run_in_executor(None, _sync_fetch)
            
        except Exception as e:
            logger.warning(f"[SmartHTTP] ScraperAPI failed: {e}")
            return None


<<<<<<< HEAD
async def _fetch_scrapedo(
    url: str,
    timeout: int = 15,
    render: bool = False,
    wait_until: str = "domcontentloaded",
    custom_wait: int = 0,
) -> Optional[str]:
    """
    Scrape.do unblocking fetch using aiohttp.
    """
    if not settings.SCRAPE_DO_API_KEY:
        return None

    async with _scrapedo_semaphore:
        try:
            import aiohttp
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            params = {
                "token": settings.SCRAPE_DO_API_KEY,
                "url": url,
                "timeout": str(max(5000, min(timeout * 1000, 120000))),
            }
            if render:
                params["render"] = "true"
                params["waitUntil"] = wait_until
                if custom_wait > 0:
                    params["customWait"] = str(min(custom_wait, 35000))

            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.scrape.do", params=params, headers=headers, timeout=timeout) as response:
                    if response.status in (401, 403):
                        logger.warning("[SmartHTTP] Scrape.do authorization failed; continuing with other fetch methods.")
                        return None
                    response.raise_for_status()
                    return await response.text()
            
        except Exception as e:
            logger.warning(f"[SmartHTTP] Scrape.do failed: {e}")
            return None


=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
# ── Core waterfall function ───────────────────────────────────────────────────

async def smart_fetch(
    url:         str,
    tier:        str = "urllib",
    timeout:     int = 12,         # kept for playwright, HTTP methods use PER_METHOD_TIMEOUT
    retailer:    str = "",
    playwright_scraper=None,
    wait_selector: str = "body",
) -> tuple[Optional[str], str, int]:
    """
    Universal fetch — ALL retailers, ALL input types.

    Strategy: PARALLEL RACE (not sequential waterfall)
    ─────────────────────────────────────────────────
    All 3 HTTP methods (urllib, curl_cffi, httpx) start SIMULTANEOUSLY.
    Whichever responds first with a valid page WINS. Others are cancelled.
    Target: every fetch < 1000ms.

    Tier controls preference (tie-breaking when multiple succeed at same time):
      amazon.in  (tier=urllib)    → prefers urllib   if tie
      flipkart   (tier=curl_cffi) → prefers curl_cffi if tie
      ajio.com   (tier=httpx)     → prefers httpx     if tie

    Playwright is GUARANTEED fallback but runs separately (always >1s — real browser).

    Returns: (html, method_used, fetch_time_ms)
    """
    # ── HTTP method constants ─────────────────────────────────────────────────
    PER_METHOD_TIMEOUT_MS = 900   # each method gets 900ms
    PER_METHOD_TIMEOUT_S  = PER_METHOD_TIMEOUT_MS / 1000

    label   = retailer or url[:40]
    loop    = asyncio.get_event_loop()
    t_start = time.monotonic()

    # Tier → preferred order for tie-breaking
    pref_order = WATERFALL_ORDER.get(tier, WATERFALL_ORDER["urllib"])

    # ── Playwright direct (for known JS-only sites) ───────────────────────────
    if tier == "playwright":
        logger.debug(f"[{retailer}] 🎭 Playwright direct (JS-only site)")
        html = await _playwright_fetch_standalone(url, wait_selector, timeout)
        total_ms = int((time.monotonic() - t_start) * 1000)
        if html and not _is_blocked(html):
            logger.info(f"[{retailer}] 🎭 Playwright: {total_ms}ms")
            return html, "playwright", total_ms
        return None, "all_failed", total_ms

    # ── Race all 3 HTTP methods in parallel ───────────────────────────────────
    METHOD_FNS = {
        "urllib":    _fetch_urllib,
        "curl_cffi": _fetch_curl_cffi,
        "httpx":     _fetch_httpx,
    }

    # Skip methods that aren't in the order (only run relevant ones)
    race_methods = [m for m in ["urllib", "curl_cffi", "httpx"] if m in pref_order]

    # ── Professional Mode: Prioritize ScraperAPI for Major Retailers ──────────
    # For sites with aggressive blocking (Amazon, Flipkart, Google Shopping),
    # we go straight to the professional proxy if a key is available.
    # This ensures "Correct Data" and real images immediately for your demo.
    high_value_retailers = ["amazon", "flipkart", "google", "nykaa", "ajio", "tatacliq"]
    is_high_value = any(hv in (retailer or "").lower() for hv in high_value_retailers)
    
<<<<<<< HEAD
    if (settings.SCRAPER_API_KEY or settings.SCRAPE_DO_API_KEY) and is_high_value:
        logger.info(f"[{retailer}] 🚀 Professional Mode: trying managed unblockers for major retailer")

        if settings.SCRAPE_DO_API_KEY:
            html = await _fetch_scrapedo(url, timeout=timeout, render=True, wait_until="domcontentloaded", custom_wait=1000)
            if html and not _is_blocked(html):
                total_ms = int((time.monotonic() - t_start) * 1000)
                logger.info(f"[{retailer}] ✅ Scrape.do (Priority) won in {total_ms}ms")
                return html, "scrapedo", total_ms

        if settings.SCRAPER_API_KEY:
            html = await _fetch_scraperapi(url)
            if html and not _is_blocked(html):
                total_ms = int((time.monotonic() - t_start) * 1000)
                logger.info(f"[{retailer}] ✅ ScraperAPI (Priority) won in {total_ms}ms")
                return html, "scraperapi", total_ms

        logger.warning(f"[{retailer}] ⚠️ Managed unblocker priority failed or returned block page. Falling back to HTTP race.")
=======
    if settings.SCRAPER_API_KEY and is_high_value:
        logger.info(f"[{retailer}] 🚀 Professional Mode: Using ScraperAPI immediately for major retailer")
        html = await _fetch_scraperapi(url)
        if html and not _is_blocked(html):
            total_ms = int((time.monotonic() - t_start) * 1000)
            logger.info(f"[{retailer}] ✅ ScraperAPI (Priority) won in {total_ms}ms")
            return html, "scraperapi", total_ms
        else:
            logger.warning(f"[{retailer}] ⚠️ ScraperAPI priority failed or returned block page. Falling back to HTTP race.")
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3

    async def _timed_fetch(method: str) -> tuple[str, Optional[str]]:
        """Run one HTTP method with per-method timeout, return (method, html)."""
        fn = METHOD_FNS[method]
        try:
            html = await asyncio.wait_for(
                loop.run_in_executor(None, fn, url, PER_METHOD_TIMEOUT_S),
                timeout=PER_METHOD_TIMEOUT_S + 0.05   # slight buffer
            )
            return method, html
        except (asyncio.TimeoutError, Exception):
            return method, None

    # Fire all tasks simultaneously
    tasks = {method: asyncio.create_task(_timed_fetch(method)) for method in race_methods}
    
    # ── Attempt ScraperAPI (if key provided) ──────────────────────────────────
    # If the user has a professional key, we try it in parallel or as a high-priority
    # alternative if we are in a 'blocked' environment.
    scraper_api_waiter = None
    if settings.SCRAPER_API_KEY:
        scraper_api_waiter = asyncio.create_task(_fetch_scraperapi(url))

<<<<<<< HEAD
    scrape_do_waiter = None
    if settings.SCRAPE_DO_API_KEY:
        scrape_do_waiter = asyncio.create_task(_fetch_scrapedo(url, timeout=timeout, render=is_high_value, wait_until="domcontentloaded", custom_wait=1000 if is_high_value else 0))

=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    # Process results as they complete (fastest first)
    winner_html       = None
    winner_method     = None
    needs_playwright  = False   # True if HTML fetched but price missing (JS-rendered)

    pending = set(tasks.values())
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

        for task in done:
            method, html = task.result()
            elapsed_ms = int((time.monotonic() - t_start) * 1000)

            if html and not _is_blocked(html):

                # ── Accuracy check: does the HTML actually contain a price? ──
                # Prevents JS-skeleton pages from being declared a success.
                # e.g. Myntra Next.js page: HTML loads, but price is in JS → empty
                if not _has_price_signal(html):
                    if _is_js_rendered_site(html):
                        # JS-SPA detected: no HTTP method will work → need Playwright
                        needs_playwright = True
                        logger.info(
                            f"[{label}] 🔍 {method} returned JS-skeleton (no price in HTML) "
                            f"at {elapsed_ms}ms — will use Playwright"
                        )
                        # Cancel all remaining HTTP tasks — they'll all have same result
                        for t in pending:
                            t.cancel()
                        pending = set()
                        break
                    else:
                        # HTML has content but no price yet — keep waiting for others
                        logger.debug(
                            f"[{label}] ⚠️ {method} HTML has no price signal at {elapsed_ms}ms"
                        )
                        continue

                # ── Valid winner ───────────────────────────────────────────────
                # Cancel all remaining tasks
                for t in pending:
                    t.cancel()
                pending = set()

                # Prefer tier's preferred method on tie-breaking
                if winner_html is None or pref_order.index(method) < pref_order.index(winner_method or "playwright"):
                    winner_html   = html
                    winner_method = method

                total_ms = int((time.monotonic() - t_start) * 1000)
                if total_ms > 1000:
                    logger.warning(f"[{label}] ⚠️ {method} over 1s: {total_ms}ms")
                else:
                    logger.debug(f"[{label}] ✅ {method} won in {total_ms}ms")

                return winner_html, winner_method, total_ms

            else:
                logger.debug(f"[{label}] ❌ {method} blocked/empty at {elapsed_ms}ms")

    # Return winner if found without price signal issue
    if winner_html:
        total_ms = int((time.monotonic() - t_start) * 1000)
        return winner_html, winner_method, total_ms

    # ── If all local HTTP failed, check ScraperAPI ────────────────────────────
    if scraper_api_waiter:
        try:
            logger.info(f"[{label}] 🚀 Attempting professional fetch via ScraperAPI...")
            html = await asyncio.wait_for(scraper_api_waiter, timeout=20.0)
            if html and not _is_blocked(html):
                total_ms = int((time.monotonic() - t_start) * 1000)
                logger.info(f"[{label}] ✅ ScraperAPI success in {total_ms}ms")
                return html, "scraperapi", total_ms
        except Exception as e:
            logger.warning(f"[{label}] ❌ ScraperAPI failed: {e}")

<<<<<<< HEAD
    if scrape_do_waiter:
        try:
            logger.info(f"[{label}] 🚀 Attempting professional fetch via Scrape.do...")
            html = await asyncio.wait_for(scrape_do_waiter, timeout=20.0)
            if html and not _is_blocked(html):
                total_ms = int((time.monotonic() - t_start) * 1000)
                logger.info(f"[{label}] ✅ Scrape.do success in {total_ms}ms")
                return html, "scrapedo", total_ms
        except Exception as e:
            logger.warning(f"[{label}] ❌ Scrape.do failed: {e}")

=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    # ── All HTTP methods failed → Playwright fallback ─────────────────────────
    # Playwright unavoidably takes >1s (real Chrome launch + page render).
    # We still use it to guarantee the retailer appears in results.
    http_ms = int((time.monotonic() - t_start) * 1000)
    logger.info(f"[{label}] 🎭 All HTTP failed in {http_ms}ms — trying Playwright fallback")

    t_pw = time.monotonic()
    try:
        if playwright_scraper is not None:
            page = await playwright_scraper._get_page(url, wait_selector=wait_selector)
            html = await page.content()
            await page.context.close()
        else:
            html = await _playwright_fetch_standalone(url, wait_selector, timeout)

        pw_ms    = int((time.monotonic() - t_pw) * 1000)
        total_ms = int((time.monotonic() - t_start) * 1000)

        if html and not _is_blocked(html):
            logger.info(f"[{label}] 🎭 Playwright: {pw_ms}ms (total {total_ms}ms — HTTP race took {http_ms}ms)")
            return html, "playwright", total_ms
        else:
            logger.warning(f"[{label}] 🎭 Playwright returned block page: {pw_ms}ms")
    except Exception as e:
        pw_ms    = int((time.monotonic() - t_pw) * 1000)
        total_ms = int((time.monotonic() - t_start) * 1000)
        logger.warning(f"[{label}] 🎭 Playwright failed: {e} in {pw_ms}ms")

    total_ms = int((time.monotonic() - t_start) * 1000)
    logger.warning(f"[{label}] 💀 ALL methods failed (total {total_ms}ms)")
    return None, "all_failed", total_ms


async def _playwright_fetch_standalone(url: str, wait_selector: str, timeout: int) -> Optional[str]:
    """Fetch HTML via Playwright without needing a BaseScraper instance."""
    from app.scrapers.base import get_browser
    import random
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    ]
    browser = await get_browser()
    ctx     = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        locale="en-IN",
        timezone_id="Asia/Kolkata",
    )

    # ── Inject session cookies (logged-in scraping) ───────────────────────────
    # If we have a stored session for this domain, inject cookies so the
    # scraper arrives as a logged-in user and sees member prices.
    try:
        from app.scrapers.session_store import session_manager
        injected = await session_manager.inject_cookies(
            url.split("/")[2].replace("www.", ""),  # extract domain
            ctx
        )
        if injected:
            logger.debug(f"[SmartHTTP] 🍪 Session cookies injected for Playwright fetch: {url[:50]}")
    except Exception:
        pass   # non-critical — proceed unlogged if session store unavailable

    page = await ctx.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        try:
            await page.wait_for_selector(wait_selector, timeout=5000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)
        return await page.content()
    except Exception:
        return None
    finally:
        await ctx.close()


# ── Convenience wrappers ──────────────────────────────────────────────────────

async def fetch_for_profile(
    url: str,
    profile,                     # SiteProfile from site_profiles.py
    retailer: str = "",
    playwright_scraper=None,
) -> tuple[Optional[str], str, int]:
    """
    Fetch a URL using the correct waterfall for a given SiteProfile.
    This is what universal.py should call for ALL fetches now.

    Works identically for:
      - URL scraping    (user pastes a link)
      - Name search     (search result page URL)
      - Image search    (name → search → same as above)
    """
    tier = profile.tier if profile else "urllib"
    wait = profile.wait_selector if profile and profile.wait_selector else "body"
    return await smart_fetch(
        url=url, tier=tier, timeout=12,
        retailer=retailer or (profile.domain if profile else ""),
        playwright_scraper=playwright_scraper,
        wait_selector=wait,
    )


async def fetch_any(
    url: str,
    retailer: str = "",
    playwright_scraper=None,
) -> tuple[Optional[str], str, int]:
    """
    Fetch any URL without a profile (auto-detect best tier from domain).
    Used for brand websites and auto-discovered retailers.
    """
    from app.scrapers.site_profiles import get_profile
    profile = get_profile(url)
    return await fetch_for_profile(url, profile, retailer, playwright_scraper)
