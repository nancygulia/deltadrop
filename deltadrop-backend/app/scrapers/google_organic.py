"""
Google Organic Search Scraper (NO API KEY required)
===================================================
Scrapes Google organic web results (not Shopping) to discover product URLs
across supported Indian e-commerce platforms.

Flow:
  1. Build a shopping-focused query: "iPhone 14 buy online india amazon flipkart price"
  2. Fetch Google HTML using requests + realistic headers
  3. Parse top 10-15 links
  4. Filter to only supported domains

Fallback:
  If Google scraping fails (CAPTCHA/block), uses SerpAPI as fallback.

Production notes:
  - Respects rate limits (max 1 request per 3 seconds)
  - Rotates User-Agent on every request
  - Uses Accept-Language: en-IN for Indian results
"""
import asyncio
import logging
import random
import re
import time
from typing import Optional
from urllib.parse import quote_plus, urlparse, parse_qs, unquote

import aiohttp

logger = logging.getLogger(__name__)


# ── Supported domains for link filtering ─────────────────────────────────────

SUPPORTED_DOMAINS = {
    "amazon.in":            "Amazon.in",
    "flipkart.com":         "Flipkart",
    "myntra.com":           "Myntra",
    "ajio.com":             "AJIO",
    "reliancedigital.in":   "Reliance Digital",
    "croma.com":            "Croma",
    "nykaa.com":            "Nykaa",
    "tatacliq.com":         "Tata CLiQ",
    "cashify.in":           "Cashify",
}

# Domains that should be excluded even if they contain a supported keyword
_BLOCKED_PATTERNS = {
    "google.com", "youtube.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "reddit.com", "quora.com", "wikipedia.org",
    "linkedin.com", "pinterest.com", "medium.com",
}


# ── User agents ──────────────────────────────────────────────────────────────

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]


# ── Rate limiter (in-memory, per-process) ────────────────────────────────────

_last_google_request: float = 0.0
_MIN_DELAY = 3.0  # seconds between Google requests


def _match_supported_domain(url: str) -> Optional[str]:
    """
    Check if a URL belongs to a supported e-commerce domain.
    Returns the canonical domain key (e.g., "amazon.in") or None.
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower().replace("www.", "")

        # Block social media, search engines etc.
        for blocked in _BLOCKED_PATTERNS:
            if blocked in host:
                return None

        for domain in SUPPORTED_DOMAINS:
            if host.endswith(domain):
                return domain
    except Exception:
        pass
    return None


def _is_product_url(url: str) -> bool:
    """
    Heuristic: is this a product page (not a search/category page)?
    """
    if not url:
        return False
    u = url.lower()
    # Common product-page indicators
    product_indicators = ["/dp/", "/p/", "/product/", "/gp/", "/itm/", "/pid="]
    # Category/search indicators
    search_indicators = ["/search?", "/category/", "/browse/", "?q=", "&q=", "/collections/"]

    has_product = any(ind in u for ind in product_indicators)
    has_search = any(ind in u for ind in search_indicators)

    if has_search and not has_product:
        return False
    # For supported domains, even generic URLs might be product pages
    return True


def _build_search_query(user_query: str) -> str:
    """
    Build a shopping-focused Google search query.
    Example: "iPhone 14" → "iPhone 14 buy online india amazon flipkart price"
    """
    q = user_query.strip()
    # Don't add shopping keywords if user already included them
    shopping_keywords = ["buy", "price", "online", "india", "amazon", "flipkart"]
    has_keywords = any(kw in q.lower() for kw in shopping_keywords)

    if not has_keywords:
        q = f"{q} buy online india amazon flipkart price"
    return q


def _extract_links_from_html(html: str) -> list[str]:
    """
    Extract real URLs from Google search results HTML.
    Handles both /url?q= redirects and direct href links.
    """
    links: list[str] = []
    seen: set[str] = set()

    # Pattern 1: Google redirect links — /url?q=https://www.amazon.in/...
    for match in re.finditer(r'href="/url\?q=([^"&]+)', html):
        raw = unquote(match.group(1))
        if raw.startswith("http") and raw not in seen:
            seen.add(raw)
            links.append(raw)

    # Pattern 2: Direct href links to retailers
    for match in re.finditer(r'href="(https?://(?:www\.)?(?:' +
                             '|'.join(re.escape(d) for d in SUPPORTED_DOMAINS) +
                             r')[^"]*)"', html):
        url = match.group(1)
        if url not in seen:
            seen.add(url)
            links.append(url)

    return links


class GoogleOrganicScraper:
    """
    Scrapes Google organic web results (NOT Shopping API, NOT SerpAPI)
    to discover product links from supported Indian e-commerce sites.
    """

    GOOGLE_URL = "https://www.google.com/search"

    async def search_product_links(
        self,
        query: str,
        max_links: int = 8,
    ) -> list[dict]:
        """
        Search Google for product links.

        Returns list of:
          {
            "url": "https://www.amazon.in/dp/...",
            "platform": "Amazon.in",
            "domain": "amazon.in"
          }

        Falls back to SerpAPI if Google scraping fails.
        """
        global _last_google_request

        search_query = _build_search_query(query)
        logger.info(f"[GoogleOrganic] Searching: {search_query}")

        # Enforce rate limit
        now = time.monotonic()
        elapsed = now - _last_google_request
        if elapsed < _MIN_DELAY:
            await asyncio.sleep(_MIN_DELAY - elapsed)
        _last_google_request = time.monotonic()

        links = await self._fetch_google(search_query)

        if not links:
            logger.warning("[GoogleOrganic] Google fetch failed, trying SerpAPI fallback")
            links = await self._serpapi_fallback(query)

        # Filter to supported domains + product pages
        filtered: list[dict] = []
        seen_domains: set[str] = set()

        for url in links:
            domain = _match_supported_domain(url)
            if not domain:
                continue
            if not _is_product_url(url):
                continue
            # One link per domain (best result)
            if domain in seen_domains:
                continue
            seen_domains.add(domain)

            filtered.append({
                "url": url,
                "platform": SUPPORTED_DOMAINS[domain],
                "domain": domain,
            })

            if len(filtered) >= max_links:
                break

        logger.info(
            f"[GoogleOrganic] Found {len(filtered)} product links from "
            f"{len(seen_domains)} platforms for '{query}'"
        )
        return filtered

    async def _fetch_google(self, query: str) -> list[str]:
        """Fetch Google HTML and extract links."""
        ua = random.choice(_USER_AGENTS)
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Referer": "https://www.google.com/",
        }
        params = {
            "q": query,
            "hl": "en",
            "gl": "in",
            "num": "20",  # Request 20 results to get more product links
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.GOOGLE_URL,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as response:
                    if response.status != 200:
                        logger.warning(f"[GoogleOrganic] ❌ HTTP {response.status}")
                        return []
                    html = await response.text()

            if "unusual traffic" in html.lower() or "captcha" in html.lower():
                logger.warning("[GoogleOrganic] Google CAPTCHA detected, falling back")
                return []

            links = _extract_links_from_html(html)
            logger.info(f"[GoogleOrganic] Extracted {len(links)} raw links from Google")
            return links

        except asyncio.TimeoutError:
            logger.warning("[GoogleOrganic] ⏱ Google HTTP request timed out (8s)")
            return []
        except Exception as e:
            logger.error(f"[GoogleOrganic] ❌ Fetch error: {e}")
            return []

    async def _serpapi_fallback(self, query: str) -> list[str]:
        """
        Fallback: use SerpAPI organic results (NOT shopping) for link discovery.
        Only called if free Google scraping fails.
        """
        from app.core.config import settings

        api_key = settings.SERPAPI_API_KEY
        if not api_key or "placeholder" in api_key.lower():
            logger.warning("[GoogleOrganic] No SerpAPI key for fallback")
            return []

        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "engine": "google",
                    "q": _build_search_query(query),
                    "api_key": api_key,
                    "gl": "in",
                    "hl": "en",
                    "num": "20",
                }
                async with session.get(
                    "https://serpapi.com/search.json",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        return []
                    data = await response.json()

            links = []
            for result in data.get("organic_results", []):
                link = result.get("link", "")
                if link:
                    links.append(link)

            logger.info(f"[GoogleOrganic] SerpAPI fallback: {len(links)} organic links")
            return links

        except Exception as e:
            logger.error(f"[GoogleOrganic] SerpAPI fallback error: {e}")
            return []


# ── Singleton ────────────────────────────────────────────────────────────────
google_organic_scraper = GoogleOrganicScraper()
