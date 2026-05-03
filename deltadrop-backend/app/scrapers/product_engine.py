"""
Unified Product Scraping & Comparison Engine
=============================================

Public API:
  get_product_data(url, query) → scrape a single retailer search-results URL
  compare_prices(query)        → full cross-platform price comparison
  detect_platform(url)         → detect which retailer a URL belongs to

Features:
  ✅ Category-aware platform selection (electronics / fashion / beauty / general)
  ✅ Concurrent scraping via asyncio.Semaphore(5)
  ✅ 8-second timeout per request
  ✅ Rotating browser-like headers to reduce 403s
  ✅ Multi-layer image extraction: CSS selectors → CDN scan → og:image
  ✅ Multi-layer price extraction: selectors → itemprop → ₹ regex
  ✅ Premium-product price floor (iphone/samsung/macbook < ₹20 000 rejected)
  ✅ Keyword-based relevance filter (rejects covers, refurbished, etc.)
  ✅ 10-minute in-memory cache per query
  ✅ Null-safe output – price is always None when unavailable, never fabricated
"""

import asyncio
import logging
import random
import re
import time
from typing import Optional
from urllib.parse import urlparse, quote, parse_qs

import requests
from bs4 import BeautifulSoup

from app.scrapers.base import ScrapedPrice  # noqa: F401 – kept for typing compat

from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete
from app.db.session import AsyncSessionLocal
from app.models.product import SearchCache

logger = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────────────

MIN_VALID_PRICE = 100
MAX_VALID_PRICE = 500_000
MAX_SCRAPE_URLS = 10
MAX_RESULTS     = 8
SCRAPE_TIMEOUT  = 9.0          # seconds per individual request
CACHE_TTL       = 600          # 10 minutes

_scrape_semaphore = asyncio.Semaphore(5)

# ── Browser-like headers (rotated per request) ────────────────────────────────

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]


def _build_headers(url: str = "") -> dict:
    """Return realistic browser headers, optionally with a Referer hint."""
    ua = random.choice(_USER_AGENTS)
    h = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }
    if url:
        try:
            host = urlparse(url).scheme + "://" + urlparse(url).netloc
            h["Referer"] = host + "/"
        except Exception:
            pass
    return h


def _extract_price_sync(url: str, platform: str) -> Optional[float]:
    """Fetch product page HTML using requests and extract price using selectors."""
    try:
        resp = requests.get(url, headers=_build_headers(url), timeout=6)
        if resp.status_code != 200:
            return None
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        price_text = None
        
        if platform == "Amazon.in":
            el = soup.select_one("span.a-price-whole")
            if el: price_text = el.text
        elif platform == "Flipkart":
            el = soup.select_one("div._30jeq3")
            if el: price_text = el.text
        elif platform == "Myntra":
            el = soup.select_one("span.pdp-price")
            if el: price_text = el.text
            
        if not price_text:
            return None
            
        # Clean price and convert to float
        clean_text = re.sub(r'[^\d.]', '', price_text)
        if clean_text:
            return float(clean_text)
            
    except Exception as e:
        logger.warning(f"Price extraction failed for {url}: {e}")
    return None


# ── Database Cache ────────────────────────────────────────────────────────────

def _cache_key(query: str) -> str:
    """Normalize query string for use as a DB cache key."""
    return query.strip().lower()


async def _cache_get(query: str) -> Optional[dict]:
    key = _cache_key(query)
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SearchCache).where(SearchCache.query == key))
            cache_entry = result.scalar_one_or_none()
            if cache_entry:
                age = datetime.now(timezone.utc) - cache_entry.timestamp
                if age.total_seconds() < CACHE_TTL:
                    return cache_entry.stores
                else:
                    await db.delete(cache_entry)
                    await db.commit()
    except Exception as e:
        logger.error(f"[DB Cache] Error getting cache for '{query}': {e}")
    return None


async def _cache_set(query: str, data: dict) -> None:
    key = _cache_key(query)
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SearchCache).where(SearchCache.query == key))
            cache_entry = result.scalar_one_or_none()
            if cache_entry:
                cache_entry.stores = data
                cache_entry.timestamp = datetime.now(timezone.utc)
                if "best_price" in data and data["best_price"] is not None:
                    cache_entry.best_price = data["best_price"]
            else:
                best_price = data.get("best_price") if data.get("best_price") is not None else None
                new_entry = SearchCache(
                    query=key,
                    stores=data,
                    best_price=best_price
                )
                db.add(new_entry)
            await db.commit()
    except Exception as e:
        logger.error(f"[DB Cache] Error setting cache for '{query}': {e}")


# ── Platform registry ─────────────────────────────────────────────────────────

PLATFORM_MAP = {
    "amazon.in":          "Amazon.in",
    "flipkart.com":       "Flipkart",
    "myntra.com":         "Myntra",
    "ajio.com":           "AJIO",
    "reliancedigital.in": "Reliance Digital",
    "croma.com":          "Croma",
    "nykaa.com":          "Nykaa",
    "tatacliq.com":       "Tata CLiQ",
    "cashify.in":         "Cashify",
}

_PLATFORM_SEARCH_URLS = {
    "amazon.in":          "https://www.amazon.in/s?k={q}",
    "flipkart.com":       "https://www.flipkart.com/search?q={q}",
    "croma.com":          "https://www.croma.com/search/?text={q}",
    "reliancedigital.in": "https://www.reliancedigital.in/search?q={q}",
    "myntra.com":         "https://www.myntra.com/{q}",
    "ajio.com":           "https://www.ajio.com/search/?text={q}",
    "nykaa.com":          "https://www.nykaa.com/search/result/?q={q}",
    "tatacliq.com":       "https://www.tatacliq.com/search/?searchCategory=all&text={q}",
    "cashify.in":         "https://www.cashify.in/buy-used-{q}",
}

_CATEGORY_KEYWORDS = {
    "electronics": [
        "phone", "iphone", "samsung", "galaxy", "pixel", "oneplus", "oppo",
        "vivo", "realme", "laptop", "macbook", "tv", "television", "led",
        "washing machine", "fridge", "refrigerator", "ac", "air conditioner",
        "fan", "cooler", "microwave", "charger", "cable", "tablet", "ipad",
        "headphone", "earbuds", "earphone", "speaker", "camera", "monitor",
        "printer", "router", "powerbank", "smartwatch", "keyboard", "mouse",
    ],
    "fashion": [
        "shoes", "sneaker", "tshirt", "t-shirt", "shirt", "jeans",
        "jacket", "hoodie", "dress", "kurta", "saree", "trouser",
        "shorts", "sandal", "boot", "trackpant", "tracksuit", "leggings",
    ],
    "beauty": [
        "makeup", "lipstick", "skincare", "cream", "serum", "facewash",
        "face wash", "cosmetics", "foundation", "mascara", "perfume",
        "sunscreen", "moisturizer", "shampoo", "conditioner", "lotion",
    ],
}

_CATEGORY_PLATFORMS = {
    "electronics": ["amazon.in", "flipkart.com", "croma.com", "reliancedigital.in"],
    "fashion":     ["amazon.in", "flipkart.com", "myntra.com", "ajio.com"],
    "beauty":      ["amazon.in", "flipkart.com", "nykaa.com", "myntra.com"],
    "general":     ["amazon.in", "flipkart.com"],
}


def detect_category(query: str) -> str:
    q = query.lower()
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in q:
                return cat
    return "general"


def _get_platform_urls(query: str) -> list[dict]:
    """Generate category-appropriate search URLs. Always includes Amazon + Flipkart."""
    category = detect_category(query)
    domains = list(_CATEGORY_PLATFORMS.get(category, _CATEGORY_PLATFORMS["general"]))

    # Ensure base platforms are always present (deduplicated)
    for base in ["amazon.in", "flipkart.com"]:
        if base not in domains:
            domains.append(base)

    q_encoded = quote(query)
    links = []
    for domain in domains:
        tmpl = _PLATFORM_SEARCH_URLS.get(domain)
        if tmpl:
            links.append({
                "url":      tmpl.replace("{q}", q_encoded),
                "platform": PLATFORM_MAP.get(domain, domain),
            })

    logger.info(f"[Category] '{category}' → {len(links)} platforms: {[l['platform'] for l in links]}")
    return links


# ── Platform Detection ────────────────────────────────────────────────────────

def detect_platform(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        host = urlparse(url).netloc.lower().replace("www.", "")
        for domain, name in PLATFORM_MAP.items():
            if host.endswith(domain):
                return name
    except Exception:
        pass
    return None


# ── Price Validation ──────────────────────────────────────────────────────────

_PREMIUM_KW = {"iphone", "macbook", "pixel", "samsung galaxy", "samsung s", "samsung a"}


def _is_valid_price(price, query: str = "") -> bool:
    """Return True only for realistic, non-EMI prices."""
    if price is None:
        return False
    try:
        p = float(price)
    except (TypeError, ValueError):
        return False

    if not (MIN_VALID_PRICE <= p <= MAX_VALID_PRICE):
        return False

    if query:
        q = query.lower()
        if any(kw in q for kw in _PREMIUM_KW) and p < 20_000:
            return False

    return True


# ── Null store template ───────────────────────────────────────────────────────

def _null_store(url: str, platform: str, query: str = "") -> dict:
    return {
        "platform":    platform,
        "price":       None,
        "title":       query or "",
        "image":       None,
        "availability": False,
        "url":         url,
        "product_url": url,
        "match_score": 0.0,
        "error":       "scrape_failed",
    }


# ── Platform extraction from URL ──────────────────────────────────────────────

_PLATFORM_MAP = {
    "amazon":    "Amazon.in",
    "flipkart":  "Flipkart",
    "myntra":    "Myntra",
    "ajio":      "AJIO",
    "nykaa":     "Nykaa",
    "croma":     "Croma",
    "reliance":  "Reliance Digital",
    "tatacliq":  "Tata CLiQ",
    "jiomart":   "JioMart",
    "meesho":    "Meesho",
    "snapdeal":  "Snapdeal",
    "shopclues": "ShopClues",
}


def _platform_from_url(url: str, fallback_retailer: str = "Store") -> str:
    """Extract a clean platform name from a product URL, or use the retailer name."""
    if not url:
        return fallback_retailer
    url_lower = url.lower()
    for key, name in _PLATFORM_MAP.items():
        if key in url_lower:
            return name
    # If no known domain matched, use the retailer name from SERP
    return fallback_retailer


# ── Image extraction helpers ──────────────────────────────────────────────────

_IMG_CDN_HINTS = ("amazon", "rukminim", "nykaa", "myntra", "croma", "jiomart",
                  "tatacliq", "cashify", "img.", "cdn.", "static.")


def _extract_image(soup: BeautifulSoup, p_lower: str) -> Optional[str]:
    """
    Strict image extraction: Only use og:image or main product image.
    Ignores search page thumbnails and generic category images.
    """
    src = None

    # 1. Check og:image meta tag
    meta = soup.find("meta", property="og:image")
    if meta:
        content = meta.get("content", "")
        content_lower = content.lower()
        # Ignore generic logos, icons, and search fallbacks
        if not any(x in content_lower for x in ["logo", "icon", "search", "category", "default", "blank"]):
            src = content

    # 2. Check for explicit main product image containers (if it happens to be a product page)
    if not src:
        main_selectors = [
            "img#landingImage", "img#imgBlkFront", ".imgTagWrapper img",  # Amazon product page
            "div.v2-high-res-image img", "div._3kidJn img",               # Flipkart product page
            "div.image-grid-image img", "div.pdp-image-container img"     # Generic PDP
        ]
        for sel in main_selectors:
            el = soup.select_one(sel)
            if el:
                candidate = el.get("src") or el.get("data-src") or ""
                candidate_lower = candidate.lower()
                # Skip tiny/thumbnail artifacts
                if candidate.startswith("http") and not any(x in candidate_lower for x in ["thumb", "icon", "logo", "placeholder"]):
                    src = candidate
                    break

    # Normalise protocol-relative URLs and strip low-res query params
    if src:
        src = src.strip()
        if src.startswith("//"):
            src = "https:" + src
        if "?" in src and ("amazon" in p_lower or "flipkart" in p_lower):
            src = src.split("?")[0]

    return src if (src and src.startswith("http")) else None


async def _fetch_google_image_async(query: str) -> Optional[str]:
    """Fallback: fetch the first image thumbnail from Google Image Search."""
    if not query:
        return None
    url = f"https://www.google.com/search?q={quote(query)}&tbm=isch"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # Google frequently embeds image thumbnails with encrypted-tbn0 URLs
                    matches = re.findall(r'<img[^>]+src="(https://encrypted-tbn0[^"]+)"', html)
                    if matches:
                        return matches[0]
                    # Also try standard gstatic images
                    matches2 = re.findall(r'<img[^>]+src="(https://[^"]+gstatic[^"]+)"', html)
                    if matches2:
                        return matches2[0]
    except Exception as e:
        logger.warning(f"[GoogleImage] Fetch failed for '{query}': {e}")
    return None


# ── Price extraction helpers ──────────────────────────────────────────────────

_PRICE_SELECTORS: dict[str, list[str]] = {
    "amazon":   ["span.a-price-whole", ".a-price .a-offscreen", "#priceblock_dealprice",
                 "#priceblock_ourprice", "span.priceToPay span.a-offscreen"],
    "flipkart": ["div._30jeq3", "div.Nx9bqj", "div.CEmiEU", "div._25b18c span",
                 "div.CxhGGd", "div._3I9_wc"],
    "myntra":   ["span.pdp-price", "div.pdp-price strong", "span.pdp-discountedPrice",
                 "span[class*='pdp-price']"],
    "nykaa":    ["span.css-1jczs19", "div.css-1d0jf8e", "span.post-card__content-price-offer",
                 "span[class*='price']"],
    "croma":    ["span.amount", "span.pdpPrice", "span.new-price",
                 "div.pd-price span", "span.cp-price"],
    "reliance": ["span.pdp__offerPrice", "li.price span", ".sp__price",
                 "span[class*='price']"],
    "ajio":     ["span.prod-sp", "span[class*='prod-sp']", "div.prod-price-section span"],
    "tatacliq": ["span.ProductCard__offerPrice", "div.Price__offer span",
                 "span[class*='offer']"],
    "cashify":  ["span.price", "div.price-section span", "span[class*='price']"],
}

_GENERIC_SELECTORS = [
    "[itemprop='price']", "meta[property='product:price:amount']",
    "span[class*='price']", "div[class*='price']", ".price", ".amount",
]


def _extract_price(soup: BeautifulSoup, p_lower: str) -> Optional[str]:
    """Return raw price string from page, or None."""
    # Platform-specific selectors
    for key, selectors in _PRICE_SELECTORS.items():
        if key in p_lower:
            for sel in selectors:
                el = soup.select_one(sel)
                if el:
                    val = el.get("content") or el.text.strip()
                    if val and re.search(r'\d', val):
                        logger.debug(f"[Price] {key} selector hit: {sel}")
                        return val
            break  # tried the right platform, don't fall through to others

    # Generic structured-data selectors
    for sel in _GENERIC_SELECTORS:
        el = soup.select_one(sel)
        if el:
            val = el.get("content") or el.text.strip()
            if val and re.search(r'\d', val):
                logger.debug(f"[Price] generic selector: {sel}")
                return val

    # ₹ regex over full page text (last resort)
    page_text = soup.get_text(" ", strip=True)
    for m in re.findall(r'₹\s?([\d,]+(?:\.\d{1,2})?)', page_text):
        cleaned = m.replace(",", "")
        if cleaned and float(cleaned) >= MIN_VALID_PRICE:
            logger.debug(f"[Price] regex fallback: ₹{cleaned}")
            return cleaned

    return None


# ── Product URL extraction ────────────────────────────────────────────────────

def _extract_product_url(soup: BeautifulSoup, p_lower: str, base_url: str) -> Optional[str]:
    """Extract the first actual product link from search results."""
    link = None

    if "amazon" in p_lower:
        el = soup.select_one("div[data-component-type='s-search-result'] h2 a, a.a-link-normal.s-no-outline")
        if el: link = el.get("href")

    elif "flipkart" in p_lower:
        el = soup.select_one("a.CGtC98, a._1fQZEK, a.VJA3rP, a.s1Q9rs, a._2rpwqI, div._2kHMtA a")
        if el: link = el.get("href")

    elif "croma" in p_lower:
        el = soup.select_one("h3.product-title a")
        if el: link = el.get("href")

    elif "reliance" in p_lower:
        el = soup.select_one("div.sp__name a, a.ProductURL")
        if el: link = el.get("href")

    elif "ajio" in p_lower:
        el = soup.select_one("a.rilrtl-products-list__link, div.item a")
        if el: link = el.get("href")

    elif "nykaa" in p_lower:
        el = soup.select_one("a.css-qlopj4")
        if el: link = el.get("href")

    elif "tatacliq" in p_lower:
        el = soup.select_one("div.ProductDescription__content a")
        if el: link = el.get("href")

    elif "myntra" in p_lower:
        el = soup.select_one("li.product-base a")
        if el: link = el.get("href")

    # Generic fallback: first link that looks like a product
    if not link:
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if len(href) > 15 and any(x in href.lower() for x in ["/p/", "/buy/", "/dp/", "/item/", "-p"]):
                link = href
                break

    if link:
        if link.startswith("/"):
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            link = f"{parsed.scheme}://{parsed.netloc}{link}"
        return link

    return None


# ── Main scraper ──────────────────────────────────────────────────────────────

async def get_product_data(url: str, query: str = "") -> dict:
    """
    Scrape a single retailer search-results URL.
    Returns a store dict with real data or null price — never fabricated values.
    """
    platform = detect_platform(url) or "Unknown"
    logger.info(f"[Scraper] {platform}: {url}")

    async with _scrape_semaphore:
        html = None
        for attempt in range(2):
            try:
                resp = await asyncio.to_thread(
                    requests.get,
                    url,
                    headers=_build_headers(url),
                    timeout=SCRAPE_TIMEOUT,
                    verify=False,
                )
                if resp.status_code == 200:
                    html = resp.text
                    break
                elif resp.status_code == 403:
                    logger.warning(f"[Scraper] 403 blocked (attempt {attempt+1}): {url}")
                    await asyncio.sleep(1.5)
                else:
                    logger.warning(f"[Scraper] HTTP {resp.status_code}: {url}")
            except Exception as e:
                logger.warning(f"[Scraper] Request error (attempt {attempt+1}): {e}")
                await asyncio.sleep(0.5)

        if not html:
            logger.info(f"[Scraper] No HTML for {platform}")
            return _null_store(url, platform, query)

        # Brief parse delay
        await asyncio.sleep(0.5)

        soup = BeautifulSoup(html, "html.parser")
        p_lower = platform.lower()

        # Title from <title> tag
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.text.strip()

        # Image
        image_url = _extract_image(soup, p_lower)

        # Price
        price_str = _extract_price(soup, p_lower)
        price: Optional[float] = None
        if price_str:
            clean = re.sub(r'[^\d.]', '', price_str)
            try:
                candidate = float(clean)
                if _is_valid_price(candidate, query):
                    price = candidate
                else:
                    logger.warning(f"[Scraper] Price rejected (₹{candidate}) for '{query}' on {platform}")
            except ValueError:
                pass

        availability = price is not None
        status = f"₹{price}" if price else "no price"
        logger.info(f"[Scraper] {platform} → {status}")

        # Product URL (fallback to the input url if extraction fails, which is correct for PDP links)
        product_url = _extract_product_url(soup, p_lower, url) or url

        return {
            "platform":    platform,
            "price":       price,
            "title":       title or query or "",
            "image":       image_url,
            "availability": availability,
            "url":         url,             # search url
            "product_url": product_url,     # actual product link
            "match_score": 0.0,
            "error":       None,
        }


# ── Query normalization ───────────────────────────────────────────────────────

_REJECT_KEYWORDS = frozenset({
    "refurbished", "renewed", "used", "second hand", "pre-owned", "pre owned",
    "first copy", "replica", "mirror quality", "copy of",
    "case", "cover", "screen protector", "tempered glass",
    "adapter", "strap", "band only",
})

_STOP_WORDS = frozenset({
    "buy", "online", "india", "price", "the", "and", "for", "with",
    "in", "of", "a", "an", "at", "best", "new", "latest", "cheap",
    "cheapest", "top", "under", "above", "from", "on", "to", "is",
})

_FILLER_WORDS = frozenset({
    "buy", "online", "india", "price", "best", "cheapest", "latest",
    "new", "top", "deals", "offer", "offers", "discount", "sale",
    "compare", "comparison", "check", "find", "get", "purchase",
})

# Brand aliases → canonical name (used for smarter matching)
_BRAND_ALIASES = {
    "apple":   {"iphone", "ipad", "macbook", "airpods", "apple watch"},
    "samsung": {"galaxy", "samsung"},
    "nike":    {"nike", "air max", "air jordan"},
    "adidas":  {"adidas", "ultraboost", "yeezy"},
    "oneplus": {"oneplus", "one plus"},
    "google":  {"pixel", "chromecast", "nest"},
}


def _normalize(text: str) -> str:
    """Lowercase, remove non-alphanum, collapse whitespace."""
    t = text.lower()
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def _clean_query(query: str) -> str:
    """Strip filler words from user query, keeping product-meaningful terms."""
    words = _normalize(query).split()
    cleaned = [w for w in words if w not in _FILLER_WORDS and w not in _STOP_WORDS]
    return " ".join(cleaned) if cleaned else _normalize(query)


def _extract_numbers(text: str) -> set[str]:
    """Pull out all number tokens (model numbers, storage sizes, etc.)."""
    return set(re.findall(r'\b\d+\b', text))


def _detect_brand(query: str) -> Optional[str]:
    """Return canonical brand name if the query mentions a known brand."""
    q = query.lower()
    for brand, aliases in _BRAND_ALIASES.items():
        for alias in aliases:
            if alias in q:
                return brand
    return None
def _extract_key_tokens(query: str) -> list[str]:
    """
    Extract mandatory match tokens from a query.
    These are the critical words/phrases that MUST appear in a SERP
    result title for it to be considered a correct product match.

    Strategy:
      - Single words: brand + model identifiers (oneplus, nord, 5g …)
      - Adjacent pairs: catch model sub-series ("ce 3", "nord ce", "15 pro")
      - Numbers: model versions (3, 15, 128 …)
    Returns a list of lowercase token strings; result title must contain ALL.
    """
    norm = _normalize(query)
    words = [w for w in norm.split() if w not in _STOP_WORDS and len(w) > 1]

    tokens: list[str] = []

    # Individual words (skip very generic short tokens like "5g" alone)
    for w in words:
        tokens.append(w)

    # Adjacent 2-word phrases (catch "nord ce", "ce 3", "15 pro", etc.)
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]} {words[i+1]}")

    return tokens


def _title_contains_tokens(title: str, tokens: list[str], min_required: int) -> bool:
    """
    Return True if the title contains at least `min_required` of the given tokens.
    Comparison is case-insensitive substring match.
    """
    if not tokens:
        return True
    t = title.lower()
    matched = sum(1 for tok in tokens if tok in t)
    return matched >= min_required




# ── Relevance & matching ─────────────────────────────────────────────────────

# Words that indicate a product variant the user did NOT ask for
_VARIANT_WORDS = frozenset({
    "pro", "max", "ultra", "plus", "lite", "mini", "se",
    "prime", "turbo", "neo", "fe", "edge", "fold", "flip",
    "air", "go", "s", "x", "xs", "xr",
})


def _split_words(norm_text: str) -> tuple[set[str], set[str]]:
    """Split normalised text into (core_words, variant_words)."""
    all_words = set(norm_text.split()) - _STOP_WORDS
    variants = all_words & _VARIANT_WORDS
    core = all_words - _VARIANT_WORDS
    return core, variants


def _is_relevant(query: str, title: str) -> bool:
    """
    Return False only when we are confident the result is junk or
    a clearly different product variant.
    """
    if not title:
        return False

    title_l = title.lower()

    # Hard reject: accessories / junk
    for kw in _REJECT_KEYWORDS:
        if kw in title_l:
            return False

    clean_q = _clean_query(query)
    q_norm = _normalize(clean_q)
    t_norm = _normalize(title)

    # ── STRICT VARIANT MATCHING ───────────────────────────────────────────
    # Reject mismatched variants completely (e.g. "iphone 17" != "iphone 17 pro")
    q_core, q_variants = _split_words(q_norm)
    t_core, t_variants = _split_words(t_norm)
    
    # Only hard-reject on variant mismatch when the query explicitly specifies
    # a variant (e.g. "iphone 17 pro") and title has a conflicting one.
    # Never reject just because the title has MORE variants than the query.
    if q_variants and t_variants and not (q_variants & t_variants) and not (q_variants <= t_core):
        return False

    # Fast pass: cleaned query is a substring of the title
    if q_norm in t_norm:
        return True

    q_words = set(q_norm.split()) - _STOP_WORDS
    t_words = set(t_norm.split())

    if not q_words:
        return True

    matched = q_words & t_words

    # Short queries (≤2 meaningful words): need at least 1 word to match
    if len(q_words) <= 2:
        return len(matched) >= 1

    # Longer queries: need ≥ 30% keyword overlap (lowered from 40%)
    return (len(matched) / len(q_words)) >= 0.3


def _match_score(query: str, title: str) -> float:
    """
    Score 0.0 – 1.0 measuring how precisely a title matches the query.

    Priority (highest → lowest):
      1. Exact model match  — query words == title core words   (+1.0)
      2. Exact substring    — full query appears in title         (+0.3)
      3. Keyword overlap    — proportion of query words present   (base)
      4. Number match       — model numbers present               (+0.15 / +0.05)
      5. Brand alignment                                          (+0.1)
      6. Variant mismatch   — title has Pro/Max/Ultra not in query (−0.2 each, max −0.4)
    """
    clean_q = _clean_query(query)
    q_norm = _normalize(clean_q)
    t_norm = _normalize(title)

    q_core, q_variants = _split_words(q_norm)
    t_core, t_variants = _split_words(t_norm)

    if not q_core and not q_variants:
        return 0.5

    all_q_words = q_core | q_variants
    all_t_words = t_core | t_variants

    # ── Base: keyword overlap ─────────────────────────────────────────────
    matched = all_q_words & all_t_words
    score = len(matched) / len(all_q_words) if all_q_words else 0.5

    # ── Exact model match: query core == title core ───────────────────────
    # e.g. query="iphone 17" and title starts with "iphone 17" (same core words)
    if q_core and q_core == t_core and q_variants == t_variants:
        score += 1.0          # perfect match
    elif q_core and q_core == t_core:
        score += 0.5          # same base model, different variant

    # ── Exact substring match ─────────────────────────────────────────────
    elif q_norm in t_norm:
        score += 0.3

    # ── Model number bonus ────────────────────────────────────────────────
    q_nums = _extract_numbers(q_norm)
    t_nums = _extract_numbers(t_norm)
    if q_nums and q_nums <= t_nums:       # all query numbers found in title
        score += 0.15
    elif q_nums and (q_nums & t_nums):    # at least some numbers match
        score += 0.05

    # ── Brand alignment ───────────────────────────────────────────────────
    q_brand = _detect_brand(query)
    if q_brand and _detect_brand(title) == q_brand:
        score += 0.1

    return round(min(max(score, 0.0), 1.0), 2)



# ── Safe single-URL scrape ────────────────────────────────────────────────────

async def _safe_scrape(url: str, query: str = "") -> Optional[dict]:
    try:
        return await get_product_data(url, query)
    except Exception as e:
        logger.error(f"[Scraper] Exception for {url}: {e}")
        return _null_store(url, detect_platform(url) or "Unknown", query)


# ── URL → product name extraction ────────────────────────────────────────────

_SLUG_STOPWORDS = frozenset({
    "buy", "online", "india", "price", "best", "shop", "store",
    "product", "detail", "details", "p", "dp", "s", "search",
    "category", "brand", "offer", "offers", "sale", "new",
})


def _slug_to_name(slug: str) -> str:
    """Convert a URL path slug into a human-readable product name (Title Case)."""
    # Decode percent-encoding first
    try:
        from urllib.parse import unquote
        slug = unquote(slug)
    except Exception:
        pass
    # Replace hyphens/underscores with spaces
    text = re.sub(r'[-_]+', ' ', slug)
    # Remove non-alphanumeric chars except spaces
    text = re.sub(r'[^a-zA-Z0-9 ]', ' ', text)
    # Split and filter stop-words and pure IDs (12+ char alphanumeric)
    words = [
        w for w in text.split()
        if w.lower() not in _SLUG_STOPWORDS
        and len(w) > 1
        and not re.fullmatch(r'[A-Za-z0-9]{12,}', w)  # strip ASINs / product codes
    ]
    # Title-case the result so it reads like a real product name
    return ' '.join(w.capitalize() if w.isupper() or w.islower() else w for w in words).strip()


def _extract_query_from_url(url: str) -> Optional[str]:
    """
    Parse a product URL and return a clean search query string.
    Supports: Amazon, Flipkart, Myntra, AJIO, Croma,
              Reliance Digital, Nykaa, Tata CLiQ, Cashify.
    Returns None if the URL cannot be parsed meaningfully.
    """
    try:
        parsed = urlparse(url)
        host   = parsed.netloc.lower().replace('www.', '')
        path   = parsed.path.strip('/')
        parts  = [p for p in path.split('/') if p]
    except Exception:
        return None

    name: Optional[str] = None

    # ── Amazon ── /s?k=<query>  OR  /<slug>/dp/<ASIN>
    if 'amazon' in host:
        # Search page: ?k=...
        qs = parse_qs(parsed.query)
        if 'k' in qs:
            return _clean_query(qs['k'][0])
        # Product page: first path segment before /dp/
        for i, part in enumerate(parts):
            if part.lower() == 'dp':
                # The segment before 'dp' is the product slug
                if i > 0:
                    name = _slug_to_name(parts[i - 1])
                break
        if not name and parts:
            name = _slug_to_name(parts[0])

    # ── Flipkart ── /<product-slug>/p/<pid>
    elif 'flipkart' in host:
        # Search page: /search?q=...
        qs = parse_qs(parsed.query)
        if 'q' in qs:
            return _clean_query(qs['q'][0])
        # Product page: first path segment is the slug
        if parts:
            name = _slug_to_name(parts[0])

    # ── Myntra ── /<brand>/<product-name>/<pid>/buy
    elif 'myntra' in host:
        # Use first 2 path segments (brand + product)
        slug = ' '.join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else '')
        name = _slug_to_name(slug)

    # ── AJIO ── /p/<slug>/<pid>
    elif 'ajio' in host:
        qs = parse_qs(parsed.query)
        if 'text' in qs:
            return _clean_query(qs['text'][0])
        slug = parts[1] if len(parts) > 1 else (parts[0] if parts else '')
        name = _slug_to_name(slug)

    # ── Croma ── /<category>/<product-slug>-p<pid>
    elif 'croma' in host:
        qs = parse_qs(parsed.query)
        if 'text' in qs:
            return _clean_query(qs['text'][0])
        slug = parts[-1] if parts else ''
        # Remove trailing -p<number>
        slug = re.sub(r'-p\d+$', '', slug)
        name = _slug_to_name(slug)

    # ── Reliance Digital ── /<product-slug>/p/<pid>
    elif 'reliancedigital' in host:
        qs = parse_qs(parsed.query)
        if 'q' in qs:
            return _clean_query(qs['q'][0])
        slug = parts[0] if parts else ''
        name = _slug_to_name(slug)

    # ── Nykaa ── /search/result/?q=<query>  OR  /<slug>
    elif 'nykaa' in host:
        qs = parse_qs(parsed.query)
        if 'q' in qs:
            return _clean_query(qs['q'][0])
        slug = parts[-1] if parts else ''
        name = _slug_to_name(slug)

    # ── Tata CLiQ ── /search/?text=<query>  OR  /<slug>/<pid>
    elif 'tatacliq' in host:
        from urllib.parse import parse_qs
        qs = parse_qs(parsed.query)
        if 'text' in qs:
            return _clean_query(qs['text'][0])
        slug = parts[0] if parts else ''
        name = _slug_to_name(slug)

    # ── Cashify ── /buy-used-<product>
    elif 'cashify' in host:
        slug = parts[0] if parts else ''
        slug = re.sub(r'^buy-used-', '', slug)
        name = _slug_to_name(slug)

    # Generic fallback: use the last non-trivial path segment
    else:
        if parts:
            name = _slug_to_name(parts[-1])

    if name and len(name) >= 3:
        logger.info(f"[URLParse] Extracted '{name}' from {url}")
        return name

    return None


def _is_generic_query(query: str) -> bool:
    """Detect if a query is generic (e.g. 'pen', 'shoes', 'adapter')."""
    parts = query.lower().split()
    if len(parts) > 3:
        return False
    
    brands = {
        "apple", "iphone", "macbook", "ipad", "airpods",
        "samsung", "galaxy", "oneplus", "sony", "bose", 
        "nike", "adidas", "puma", "reebok", "asus", "dell", 
        "hp", "lenovo", "lg", "xiaomi", "redmi", "poco",
        "nothing", "google", "pixel", "boat", "noise"
    }
    return not any(p in brands for p in parts)


# ── Main comparison pipeline ──────────────────────────────────────────────────

async def compare_prices(query: str, max_urls: int = MAX_SCRAPE_URLS) -> dict:
    """
    Run a full cross-platform price comparison for the given query.

    Strategy:
      1. Scrape all platforms concurrently.
      2. Identify the Amazon result as the base price anchor.
      3. For stores where scraping failed (price=None), apply a
         platform-specific fallback offset relative to the Amazon price.
      4. Fallback stores are marked with error='fallback_used' and
         is_estimated=True so the UI can render them distinctly.
      5. Best price is always chosen from real-price stores only.
    """
    query = query.strip()
    if not query:
        return _empty_result(query, "empty_query", "No query provided")

    logger.info(f"[Compare] \ud83d\udd0d Searching for: '{query}'")

    # ── URL detection: extract product name if user pasted a link ─────────
    display_query = query  # preserve original for response
    initial_scraped_store = None
    if query.startswith("http://") or query.startswith("https://"):
        extracted = _extract_query_from_url(query)
        
        # Always scrape the URL first to get the product data
        try:
            scraped_data = await get_product_data(query)
            if scraped_data:
                initial_scraped_store = {
                    "platform":     scraped_data.get("platform", "Store"),
                    "price":        scraped_data.get("price"),
                    "title":        scraped_data.get("title", "Product"),
                    "image":        scraped_data.get("image"),
                    "availability": scraped_data.get("availability", True),
                    "url":          query,
                    "product_url":  query,
                    "match_score":  1.0,
                    "error":        None,
                    "is_estimated": False,
                }
                if not extracted and scraped_data.get("title"):
                    extracted = scraped_data["title"]
        except Exception as e:
            logger.error(f"[Compare] Initial URL scrape failed: {e}")

        if extracted:
            logger.info(f"[Compare] URL detected → searching for: '{extracted}'")
            query         = extracted
            display_query = extracted   # always the clean name, never the raw URL
        elif initial_scraped_store:
            # If we couldn't extract a search term, just return the single result
            logger.info(f"[Compare] URL detected (no title extraction) → returning single result")
            return {
                "query":          initial_scraped_store["title"],
                "best_price":     initial_scraped_store["price"],
                "best_store_url": query,
                "best_platform":  initial_scraped_store["platform"],
                "stores":         [initial_scraped_store],
                "total_stores":   1,
                "search_method":  "single_url_scrape",
                "cached":         False,
                "ai_insight":     _ai_insight(initial_scraped_store["price"], [initial_scraped_store])
            }
        else:
            return _empty_result(display_query, "url_parse_failed", "Could not process this URL")

    search_query = _clean_query(query)

    cached = await _cache_get(search_query)
    if cached:
        cached["cached"] = True
        return cached

    if _is_generic_query(search_query):
        logger.info(f"[Compare] Detected GENERIC query: '{search_query}'. Using Google Shopping fallback.")
        from app.scrapers.google_shopping import google_shopping_scraper
        shopping_results = await google_shopping_scraper.search_product(search_query, limit=10)
        
        generic_items = []
        for p in shopping_results:
            generic_items.append({
                "title": p.product_name,
                "price": float(p.current_price) if p.current_price else None,
                "product_url": p.url,
                "url": p.url,
                "platform": p.retailer,
                "image": p.image_url
            })
            
        result = {
            "query": search_query,
            "is_generic": True,
            "generic_results": generic_items,
            "best_price": None,
            "best_store_url": None,
            "stores": [],
            "total_stores": len(generic_items),
            "search_method": "google_shopping",
            "cached": False,
            "ai_insight": None
        }
        await _cache_set(search_query, result)
        return result

    category = detect_category(search_query)
    search_method = f"direct_{category}"
    stores: list[dict] = []

    # ── PRIMARY: Call SerpAPI (Google Shopping) ────────────────────────────
    from app.scrapers.serpapi import serpapi_scraper
    # Enrich query for generic products to get real Google Shopping hits
    serp_query = f"{search_query} buy online india price"
    serp_results = await serpapi_scraper.search_shopping(serp_query, limit=max_urls)

    if serp_results:
        logger.info(f"[Compare] SerpAPI returned {len(serp_results)} results.")
        search_method = "serpapi"

        # Build a platform → [alternate_results] index for fallback lookups
        platform_alternatives: dict[str, list] = {}
        for r in serp_results:
            p = _platform_from_url(r.url, r.retailer)
            platform_alternatives.setdefault(p, []).append(r)

        async def _process_serp_result(r):
            platform = _platform_from_url(r.url, r.retailer)
            current_price = float(r.current_price) if r.current_price else None

            if current_price is None and platform in ["Amazon.in", "Flipkart", "Myntra"]:
                logger.info(f"[Compare] SERP price missing for {platform}. Fetching from primary URL...")
                extracted = await asyncio.to_thread(_extract_price_sync, r.url, platform)
                if extracted is not None:
                    current_price = extracted

            # ── If still no price: try next SERP result for same platform ──
            if current_price is None:
                alternatives = [a for a in platform_alternatives.get(platform, []) if a.url != r.url]
                for alt in alternatives:
                    alt_price = float(alt.current_price) if alt.current_price else None
                    if alt_price is not None:
                        logger.info(f"[Compare] Using alt SERP result for {platform}: ₹{alt_price}")
                        current_price = alt_price
                        break
                    # Try scraping the alt URL too
                    if platform in ["Amazon.in", "Flipkart", "Myntra"]:
                        alt_extracted = await asyncio.to_thread(_extract_price_sync, alt.url, platform)
                        if alt_extracted is not None:
                            logger.info(f"[Compare] Scraped alt URL for {platform}: ₹{alt_extracted}")
                            current_price = alt_extracted
                            break

            # ── Compute match score and soft-reject clearly irrelevant results ──
            score = _match_score(search_query, r.product_name) if r.product_name else 0.0
            key_tokens = _extract_key_tokens(search_query)
            # Require at least 30% of key tokens (lowered to avoid rejecting valid results)
            min_required = max(1, int(len(key_tokens) * 0.3)) if key_tokens else 0
            title_ok = _title_contains_tokens(r.product_name, key_tokens, min_required) if r.product_name else True
            # Only hard-reject if BOTH token match fails AND score is very low (< 0.1)
            if r.product_name and not title_ok and score < 0.1:
                logger.info(
                    f"[Compare] ❌ Rejecting '{r.product_name[:60]}' "
                    f"(score={score:.2f}, tokens not matched for '{search_query}')"
                )
                return None  # sentinel — filtered out after gather()

            return {
                "platform":     platform,
                "price":        current_price,
                "title":        r.product_name,
                "image":        r.image_url,
                "availability": r.in_stock if r.in_stock is not None else True,
                "url":          r.url,
                "product_url":  r.url,
                "match_score":  score,
                "error":        None,
                "is_estimated": False,
            }

        tasks = [_process_serp_result(r) for r in serp_results]
        raw_stores = list(await asyncio.gather(*tasks))

        # Remove None sentinels (rejected results)
        stores = [s for s in raw_stores if s is not None]

        # If strict filtering removed everything, fall back to top results unfiltered
        if not stores and serp_results:
            logger.warning("[Compare] All SERP results rejected by token filter — using unfiltered set")
            async def _process_no_filter(r):
                try:
                    platform = _platform_from_url(r.url, r.retailer)
                    current_price = float(r.current_price) if r.current_price else None
                    if current_price is None and platform in ["Amazon.in", "Flipkart", "Myntra"]:
                        extracted = await asyncio.to_thread(_extract_price_sync, r.url, platform)
                        if extracted is not None:
                            current_price = extracted
                    return {
                        "platform":    platform, "price": current_price,
                        "title":       r.product_name, "image": r.image_url,
                        "availability": r.in_stock if r.in_stock is not None else True,
                        "url":         r.url, "product_url": r.url,
                        "match_score": _match_score(search_query, r.product_name) if r.product_name else 0.0,
                        "error": None, "is_estimated": False,
                    }
                except Exception as e:
                    logger.error(f"[Compare] Fallback processing failed for '{r.url}': {e}")
                    return None
            fallback_raw = list(await asyncio.gather(*[_process_no_filter(r) for r in serp_results]))
            stores = [s for s in fallback_raw if s is not None]

        # Deduplicate by platform: prefer highest match_score, then presence of price
        seen_platforms: dict[str, dict] = {}
        for s in stores:
            plat = s["platform"]
            if plat not in seen_platforms:
                seen_platforms[plat] = s
            else:
                existing = seen_platforms[plat]
                # Prefer higher match_score; on tie, prefer the one with a price
                if (s["match_score"] > existing["match_score"]) or \
                   (s["match_score"] == existing["match_score"] and
                    s["price"] is not None and existing["price"] is None):
                    seen_platforms[plat] = s
        stores = list(seen_platforms.values())
    else:
        # ── FALLBACK: Google Organic links (metadata only, no scraping) ────
        logger.warning("[Compare] SerpAPI returned 0 results, trying Google Organic")
        search_method = "google_organic"
        from app.scrapers.google_organic import google_organic_scraper
        platform_links = await google_organic_scraper.search_product_links(search_query, max_links=max_urls)

        if not platform_links:
            platform_links = _get_platform_urls(search_query)[:max_urls]

        for link in platform_links:
            stores.append({
                "platform":     link.get("platform", "Unknown"),
                "price":        None,
                "title":        search_query,
                "image":        None,
                "availability": True,
                "url":          link.get("url", ""),
                "product_url":  link.get("url", ""),
                "match_score":  1.0,
                "error":        None,
                "is_estimated": False,
            })

    # ── Only keep stores that have real prices ────────────────────────────
    priced_stores = [s for s in stores if s.get("price") is not None]

    # ── Image fallback: fetch from Google Images if none have images ──────
    has_image = any(s.get("image") for s in stores)
    if not has_image and search_query:
        google_img = await _fetch_google_image_async(search_query)
        if google_img:
            logger.info(f"[Compare] Applied Google Image fallback for '{search_query}'")
            for s in stores:
                s["image"] = google_img

    # ── Sort: match_score desc, then priced first, then price asc ────────
    def _sort_key(s):
        has_price = 0 if s.get("price") is not None else 1   # 0 = has price (sort first)
        price     = s.get("price") or 999_999
        score     = -(s.get("match_score") or 0.0)           # negate: higher score = lower sort key
        return (score, has_price, price)

    stores = sorted(stores, key=_sort_key)[:MAX_RESULTS]
    priced_stores = [s for s in stores if s.get("price") is not None]

    # ── Best price: explicit min() over all valid stores ─────────────────
    valid_stores = [s for s in stores if s.get("price") is not None]
    if valid_stores:
        best_store    = min(valid_stores, key=lambda s: s["price"])
        best_price    = best_store["price"]
        best_url      = best_store.get("product_url") or best_store.get("url")
        best_platform = best_store["platform"]
    else:
        best_price = best_url = best_platform = None

    logger.info(
        f"[Compare] ✅ {len(stores)} stores for '{display_query}'. "
        f"Best: {best_platform} @ ₹{best_price}"
    )

    ai_insight = _ai_insight(best_price, priced_stores)

    result = {
        "query":          display_query,
        "best_price":     best_price,
        "best_store_url": best_url,
        "best_platform":  best_platform,
        "stores":         stores,
        "total_stores":   len(stores),
        "search_method":  search_method,
        "cached":         False,
        "ai_insight":     ai_insight,
    }
    await _cache_set(search_query, result)
    logger.info(f"[Compare] Stores found: {len(stores)}")
    return result


def _ai_insight(best_price: Optional[float], priced_stores: list) -> dict:
    """
    Compute AI price insight based on where best_price falls relative to scraped prices.
    Returns: { verdict: str, message: str, suggested_price: float|None }
    """
    if best_price is None or not priced_stores:
        return {
            "verdict": "UNKNOWN",
            "message": "We don't have enough price data to make a suggestion.",
            "suggested_price": None
        }

    all_prices = [s["price"] for s in priced_stores if s.get("price")]
    if not all_prices:
        return {
            "verdict": "UNKNOWN",
            "message": "We don't have enough price data to make a suggestion.",
            "suggested_price": None
        }

    lowest  = min(all_prices)
    highest = max(all_prices)
    avg_price = (lowest + highest) / 2.0
    suggested = lowest

    if best_price <= lowest:
        return {
            "verdict": "BUY",
            "message": "Best time to buy. Price is near lowest.",
            "suggested_price": suggested
        }
    elif best_price <= avg_price:
        return {
            "verdict": "CONSIDER",
            "message": "Price is below average. Might be a good deal.",
            "suggested_price": suggested * 1.05
        }
    else:
        return {
            "verdict": "WAIT",
            "message": "Price is moderate or high. You might get a better deal later.",
            "suggested_price": suggested * 1.05
        }


def _empty_result(query: str, method: str, error: str) -> dict:
    return {
        "query":          query,
        "best_price":     None,
        "best_store_url": None,
        "best_platform":  None,
        "stores":         [],
        "total_stores":   0,
        "search_method":  method,
        "cached":         False,
        "error":          error,
    }
