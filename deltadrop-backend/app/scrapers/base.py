"""
Base scraper — shared Playwright browser setup, stealth headers,
retry logic, rate limiting, and structured result types.
"""
import asyncio
import logging
import re
import time
<<<<<<< HEAD
import sys
=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from playwright.async_api import (
    async_playwright, Browser, BrowserContext, Page,
    TimeoutError as PlaywrightTimeout
)

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ScrapedPrice:
    """Structured result from any scraper."""
    retailer:     str
    url:          str
    product_name: str
    current_price: Optional[Decimal]
    mrp:          Optional[Decimal]
    discount_pct: Optional[Decimal]
    in_stock:     Optional[bool] = True   # None = unknown; defaults to True to satisfy NOT NULL
    image_url:    Optional[str] = None
    brand:        Optional[str] = None
    specs:        dict          = field(default_factory=dict)
    error:        Optional[str] = None
    # Fetch diagnostics — how long did it take and which method worked
    fetch_time_ms:  Optional[int] = None   # total ms to get the HTML
    fetch_method:   Optional[str] = None   # "urllib" | "curl_cffi" | "httpx" | "playwright"

    @property
    def safe_in_stock(self) -> bool:
        """Always returns a real bool. Never passes None to the DB."""
        return True if self.in_stock is None else bool(self.in_stock)

    @property
    def is_valid(self) -> bool:
        return self.current_price is not None and self.error is None


# ── User agents pool ──────────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# Shared browser instance across scrapers
_browser: Optional[Browser] = None
_playwright = None
<<<<<<< HEAD
_playwright_disabled = True

# ── Windows Compatibility ──────────────────────────────────────────────────
if sys.platform == "win32":
    try:
        # We only set the policy if no loop is running. 
        # In FastAPI, this should ideally be handled in main.py.
        policy = asyncio.get_event_loop_policy()
        if not isinstance(policy, asyncio.WindowsSelectorEventLoopPolicy):
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception as e:
        logger.debug(f"[Playwright] Windows event-loop check: {e}")



async def get_browser() -> Browser:
    """
    Get or create the shared Playwright browser instance.
    Includes robust error handling for Windows ProactorEventLoop issues.
    """
    global _browser, _playwright, _playwright_disabled
    
    if _playwright_disabled:
        raise RuntimeError("Playwright is currently disabled due to startup failure")

    if _browser is None or not _browser.is_connected():
        try:
            print("PLAYWRIGHT LAUNCHING")
            logger.info("[Playwright] Launching browser...")
            _playwright = await async_playwright().start()
            _browser = await _playwright.chromium.launch(
                headless=settings.SCRAPER_HEADLESS,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--window-size=1280,800",
                ],
            )
            logger.info("✅ Playwright browser launched successfully")
        except Exception as e:
            import traceback
            _playwright_disabled = True
            error_msg = str(e)
            print(f"PLAYWRIGHT ERROR: {error_msg}")
            traceback.print_exc()
            
            if "ProactorEventLoop" in error_msg or "NotImplementedError" in error_msg:
                logger.error("❌ [Playwright] Windows compatibility error. "
                             "Check event loop policy in main.py.")
            else:
                logger.error(f"❌ [Playwright] Failed to launch browser: {e}")
            
            # Clean up if partially started
            if _playwright:
                try: await _playwright.stop()
                except: pass
                _playwright = None
                
            raise RuntimeError(f"Playwright unavailable: {e}") from e

            
    return _browser



=======


async def get_browser() -> Browser:
    global _browser, _playwright
    if _browser is None or not _browser.is_connected():
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=settings.SCRAPER_HEADLESS,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
                "--window-size=1280,800",
            ],
        )
        logger.info("✅ Playwright browser launched")
    return _browser


>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
async def close_browser():
    global _browser, _playwright
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None
    logger.info("Browser closed")


class BaseScraper:
    """
    Base class for all DeltaDrop scrapers.
    Subclasses implement `scrape_url(url)` and `search_product(query)`.
    """
    RETAILER_NAME: str = "Unknown"
    BASE_URL:      str = ""

    # Per-scraper rate limit (seconds between requests)
    REQUEST_DELAY: float = 1.5

    def __init__(self):
        self._last_request: float = 0.0

    # ── Browser helpers ───────────────────────────────────────────────────────

    async def _new_context(self) -> BrowserContext:
        import random
        browser = await get_browser()
        ua = random.choice(USER_AGENTS)
        ctx = await browser.new_context(
            user_agent=ua,
            viewport={"width": 1280, "height": 800},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            extra_http_headers={
                "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
                "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT":             "1",
            },
        )
        ctx.set_default_timeout(settings.SCRAPER_TIMEOUT_MS)
        return ctx

    async def _rate_limit(self):
        """Enforce per-scraper delay between requests."""
        elapsed = time.time() - self._last_request
        if elapsed < self.REQUEST_DELAY:
            await asyncio.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request = time.time()

    async def _get_page(self, url: str, wait_selector: str = "body") -> Page:
        """Navigate to URL with rate limiting. Returns an open page."""
        await self._rate_limit()
        ctx  = await self._new_context()
        page = await ctx.new_page()

<<<<<<< HEAD
        # Enhanced anti-detection setup
        try:
            # Set realistic browser fingerprint
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                window.chrome = {
                    runtime: {},
                };
            """)
            
            # Apply playwright stealth plugin
            try:
                from playwright_stealth import stealth_async
                await stealth_async(page)
            except ImportError:
                from playwright_stealth import Stealth
                await Stealth().apply_stealth_async(page)
        except Exception as e:
            logger.debug(f"Stealth setup failed: {e}")
            # Continue without stealth
=======
        # Apply playwright stealth plugin to bypass simple captchas
        try:
            from playwright_stealth import Stealth
            await Stealth().apply_stealth_async(page)
        except Exception as e:
            logger.warning(f"playwright-stealth not applied properly: {e}")
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3

        # Block ads / tracking to speed up scrapes
        await page.route(
            "**/{ads,analytics,tracking,doubleclick,facebook}**",
            lambda route: route.abort()
        )

        await page.goto(url, wait_until="domcontentloaded", timeout=settings.SCRAPER_TIMEOUT_MS)
        try:
            await page.wait_for_selector(wait_selector, timeout=8000)
        except PlaywrightTimeout:
            pass   # proceed even if selector not found — partial data better than none
        return page

    # ── Price parsing helpers ─────────────────────────────────────────────────

    @staticmethod
    def parse_price(raw: str) -> Optional[Decimal]:
        """'₹1,49,900', '1,49,900.00', '149900' → Decimal"""
        if not raw:
            return None
        cleaned = re.sub(r"[^\d.]", "", raw.replace(",", ""))
        try:
            return Decimal(cleaned) if cleaned else None
        except Exception:
            return None

    @staticmethod
    def parse_discount(price: Optional[Decimal], mrp: Optional[Decimal]) -> Optional[Decimal]:
        if price and mrp and mrp > 0:
            pct = ((mrp - price) / mrp) * 100
            return pct.quantize(Decimal("0.01"))
        return None

    @staticmethod
    def validate_price(price: Optional[Decimal], mrp: Optional[Decimal]) -> Optional[Decimal]:
        """
        Issue 2 Fix — reject obviously wrong prices:
        - Price > MRP            → probably scraped MRP field by mistake
        - Price < MRP * 0.05     → suspiciously cheap (EMI monthly installment?)
        - Price > 10,000,000     → clearly garbage
        - Price <= 0             → invalid
        Returns the price if valid, None if suspicious.
        """
        if price is None:
            return None
        if price <= 0 or price > Decimal('10000000'):
            return None
        if mrp:
            if price > mrp * Decimal('1.05'):   # price > MRP + 5% buffer
                return None
            if price < mrp * Decimal('0.05'):   # price < 5% of MRP = EMI trap
                return None
        return price

    @staticmethod
    def canonicalize_url(url: str, retailer: str) -> str:
        """
        Issue 3 Fix — strip session tokens and affiliate params from URLs.
        Amazon: keep only /dp/ASIN  
        Flipkart: keep only /p/pid=XXXXX
        Others: strip known tracking params.
        """
        if not url:
            return url
        try:
            from urllib.parse import urlparse, urlunparse, urlencode, parse_qs
            parsed = urlparse(url)

            if 'amazon.in' in parsed.netloc:
                # Extract ASIN from path: /dp/B094XNMJ5B/...
                asin_match = re.search(r'/dp/([A-Z0-9]{10})', parsed.path)
                if asin_match:
                    return f"https://www.amazon.in/dp/{asin_match.group(1)}"

            if 'flipkart.com' in parsed.netloc:
                # Keep only pid param
                params = parse_qs(parsed.query)
                pid = params.get('pid', params.get('p', [None]))[0]
                if pid:
                    return f"https://www.flipkart.com/p/pid={pid}"

            # For all others: strip known tracking junk
            STRIP_PARAMS = {
                'ref', 'ref_', 'tag', 'linkCode', 'camp', 'creative',
                'th', 'psc', 'smid', 'dib', 'dib_tag', 'keywords',
                'sr', 'qid', 'sprefix', 'crid', 'pf_rd_r', 'pf_rd_p',
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_content',
            }
            params = parse_qs(parsed.query)
            clean  = {k: v for k, v in params.items() if k.lower() not in STRIP_PARAMS}
            new_query = urlencode({k: v[0] for k, v in clean.items()})
            return urlunparse(parsed._replace(query=new_query))
        except Exception:
            return url

    @staticmethod
    def ensure_absolute_url(url: str, base_url: str) -> str:
        """Converts relative URLs (/img.jpg) to absolute (https://site.com/img.jpg)."""
        if not url: return ""
        if url.startswith("http"): return url
        if url.startswith("//"): return f"https:{url}"
        from urllib.parse import urljoin
        return urljoin(base_url, url)

    @staticmethod
    def extract_jsonld_price(html: str) -> dict:
        """
        Issue 2 Fix — extract price from JSON-LD structured data.
        This is the most reliable price source — designed for Google,
        always contains the canonical display price (not bank offers, not EMI).
        Returns dict with keys: price, mrp, name, image, brand (all optional).
        """
        import json
        result = {}
        try:
            import re as _re
            scripts = _re.findall(
                r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                html, _re.DOTALL | _re.IGNORECASE
            )
            for raw in scripts:
                try:
                    data = json.loads(raw.strip())
                    # Handle both single object and @graph array
                    nodes = data if isinstance(data, list) else [data]
                    if '@graph' in data:
                        nodes = data['@graph']
                    for node in nodes:
                        if node.get('@type') in ('Product', 'IndividualProduct'):
                            offers = node.get('offers') or node.get('Offers')
                            if offers:
                                if isinstance(offers, list):
                                    offers = offers[0]
                                price_raw = offers.get('price') or offers.get('lowPrice')
                                if price_raw:
                                    result['price'] = Decimal(str(price_raw))
                            if node.get('name'):
                                result['name'] = node['name']
                            if node.get('image'):
                                img = node['image']
                                result['image'] = img[0] if isinstance(img, list) else img
                            brand = node.get('brand')
                            if brand:
                                result['brand'] = brand.get('name', brand) if isinstance(brand, dict) else str(brand)
                            break
                except Exception:
                    continue
        except Exception:
            pass
        return result

    @staticmethod
    def clean_name(name: str) -> str:
        """
        Issue 3 Fix — truncate Amazon-style long names.
        'Sony WH-1000XM5 Industry Leading Noise Canceling...' → 'Sony WH-1000XM5'
        Stops at the first em-dash, pipe, or excessive length (>80 chars).
        """
        if not name:
            return name
        # Stop at common separators retailers add after the real name
        for sep in [' | ', ' - with ', ' - for ', ' (For ', ',  ']:
            if sep in name:
                name = name.split(sep)[0]
        # Stop at opening parenthesis if name is still long
        if len(name) > 80 and '(' in name:
            name = name.split('(')[0].strip()
        return name.strip()[:120]   # hard cap

    # ── Relevance & Originality Filter ───────────────────────────────────────
    
    def calculate_relevance(self, query: str, product_name: str, retailer: str = "", url: str = "") -> float:
        """
        Calculate a relevance score (0.0 to 1.0) for a product result.
        Rejects fakes, first-copies, and wrong brands.
        """
        if not product_name or not query:
            return 0.0
            
        q = query.lower()
        p = product_name.lower()
        
        # 1. Anti-Fake Check: reject anything mentioning 'copy', 'replica', etc.
        fake_keywords = [
            "first copy", "replica", "mirror quality", "master copy", "copy of",
            "inspired by", "lookalike", "fake", "counterfeit", "7a quality"
        ]
        if any(fake in p for fake in fake_keywords):
            logger.info(f"[Filter] Rejected potential fake: {product_name}")
            return 0.0

        # 2. Brand Check: if a brand is in the query, it SHOULD be in the product name
        # UNLESS the retailer is the official brand site.
        query_brand = self._extract_brand(q)
        if query_brand:
            result_brand = self._extract_brand(p)
            # Check if domain or retailer name matches the brand
            source_mentions_brand = (query_brand in retailer.lower()) or (url and query_brand in url.lower())
            
            if result_brand and result_brand != query_brand:
                # User searched for Adidas, result is explicitly Nike -> REJECT
                logger.debug(f"[Filter] Brand mismatch: Query={query_brand}, Result={result_brand}")
                return 0.0
            
            if query_brand not in p and not source_mentions_brand:
                # Brand missing from both title AND source info -> REJECT in strict mode
                logger.debug(f"[Filter] Brand missing from result: {query_brand}")
                return 0.0

        # 3. Keyword Intersection: how many unique words from query are in title?
        q_words = set(re.findall(r'\w{2,}', q))
        # Remove common filler words
        stop_words = {"shoe", "shoes", "for", "men", "women", "the", "and", "with", "buy", "online", "india", "product", "official"}
        q_keywords = q_words - stop_words
        
        if not q_keywords:
            return 1.0 # fallback if no keywords left
            
        p_words = set(re.findall(r'\w{2,}', p))
<<<<<<< HEAD
        p_compact = "".join(p_words)
        matches = set(q_keywords.intersection(p_words))

        # Match split query terms against compound product names.
        # Example: "ultra boost" should match "ultraboost".
        unmatched = list(q_keywords - matches)
        for i, first in enumerate(unmatched):
            for second in unmatched[i + 1:]:
                if f"{first}{second}" in p_compact or f"{second}{first}" in p_compact:
                    matches.add(first)
                    matches.add(second)
=======
        matches = q_keywords.intersection(p_words)
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
        
        # STRICTOR OVERLAP: Must match at least 60% of keywords
        overlap_pct = len(matches) / len(q_keywords)
        if overlap_pct < 0.6:
            logger.debug(f"[Filter] Low keyword overlap ({overlap_pct:.2f}): {product_name}")
            return 0.0
            
        score = overlap_pct
        
        # Boost if it came from the official brand site
        if query_brand and (url and query_brand in url.lower()):
            score += 0.2
            
        # 4. Strict Model Number check (e.g. '5' in Ultraboost 5)
        # In strict mode, if a model number is specified in query but missing in title, it's likely a wrong item.
        model_nums = re.findall(r'\b\d{1,2}\b', q)
        for num in model_nums:
            if num not in p:
                # Harsher penalty: 0.5x. This will likely push it below the PASSED threshold.
                score *= 0.5 
                
        # 5. Accessory Penalty: if result is a case/cover but query isn't
<<<<<<< HEAD
        accessory_keywords = [
            "case", "cover", "back cover", "phone cover", "mobile cover",
            "screen protector", "tempered glass", "guard", "skin", "pouch",
            "strap", "cable", "adapter", "charger", "earphone", "earphones",
            "earbuds", "neckband", "headset", "holder", "stand", "lens protector",
        ]
=======
        accessory_keywords = ["case", "cover", "screen protector", "tempered glass", "pouch", "strap", "cable", "adapter"]
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
        is_result_accessory = any(kw in p for kw in accessory_keywords)
        is_query_accessory = any(kw in q for kw in accessory_keywords)
        
        if is_result_accessory and not is_query_accessory:
<<<<<<< HEAD
            logger.info(f"[Filter] Rejected accessory for device query: {product_name}")
            return 0.0
=======
            # Harsh penalty for accessories when searching for the device
            score *= 0.3
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
                
        return min(score, 1.0)

    def _extract_brand(self, text: str) -> Optional[str]:
        """Simple brand extraction based on common Indian retail brands."""
        # This list should ideally be shared with category_router.py
        BRANDS = [
            "adidas", "nike", "puma", "reebok", "h&m", "zara", "apple", "samsung",
            "oneplus", "boat", "noise", "sony", "lg", "hp", "dell", "lenovo",
            "mamaearth", "minimalist", "nykaa", "ajio", "myntra"
        ]
        for brand in BRANDS:
            if brand in text.lower():
                return brand
        return None

    # ── URL Normalization ────────────────────────────────────────────────────

    # ── Retry wrapper ─────────────────────────────────────────────────────────

    async def with_retry(self, coro_fn, *args, **kwargs):
        last_exc = None
        for attempt in range(1, settings.SCRAPER_MAX_RETRIES + 1):
            try:
                return await coro_fn(*args, **kwargs)
            except PlaywrightTimeout as e:
                last_exc = e
                logger.warning(f"[{self.RETAILER_NAME}] Timeout attempt {attempt}/{settings.SCRAPER_MAX_RETRIES}: {args}")
            except Exception as e:
                last_exc = e
                logger.warning(f"[{self.RETAILER_NAME}] Error attempt {attempt}: {e}")
            if attempt < settings.SCRAPER_MAX_RETRIES:
                await asyncio.sleep(2 ** attempt)   # exponential backoff

        logger.error(f"[{self.RETAILER_NAME}] All retries failed for {args}: {last_exc}")
        raise last_exc

    # ── Resilient HTTP fetch — universal profile-aware waterfall ─────────────

    async def fetch_html_with_fallback(
        self,
        url:     str,
        timeout: int = 12,
        profile=None,
    ) -> tuple[Optional[str], str, int]:
        """
        Universal HTML fetch — works for ALL retailers, ALL input types.
        Uses smart_http.smart_fetch which is profile-aware:

          amazon.in  (tier=urllib)    → urllib → curl_cffi → httpx → playwright
          flipkart   (tier=curl_cffi) → curl_cffi → httpx → urllib → playwright
          ajio.com   (tier=httpx)     → httpx → curl_cffi → urllib → playwright
          meesho     (tier=playwright)→ playwright directly

        Returns (html, method_name, fetch_time_ms)
        Playwright is GUARANTEED last resort — no retailer ever disappears.
        """
        from app.scrapers.smart_http import smart_fetch
        from app.scrapers.site_profiles import get_profile

        if profile is None:
            profile = get_profile(url)

        tier = profile.tier if profile else "urllib"
        wait = profile.wait_selector if profile and profile.wait_selector else "body"

        return await smart_fetch(
            url=url, tier=tier, timeout=timeout,
            retailer=self.RETAILER_NAME,
            playwright_scraper=self,
            wait_selector=wait,
        )


    # ── Interface (override in subclasses) ────────────────────────────────────

    async def scrape_url(self, url: str) -> ScrapedPrice:
        raise NotImplementedError

    async def search_product(self, query: str, limit: int = 5) -> list[ScrapedPrice]:
        raise NotImplementedError
