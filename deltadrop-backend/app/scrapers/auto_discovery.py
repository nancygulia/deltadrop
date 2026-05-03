"""
Auto-Discovery Engine
=====================
Automatically finds which retailers sell a product by querying Google Shopping,
then scrapes each retailer URL with the universal scraper.

This means ANY retailer in India that lists on Google Shopping gets automatically
picked up — no manual configuration needed in site_profiles.py.

How it works:
  1. Query Google Shopping for "Sony WH-1000XM5 buy india"
  2. Google Shopping returns: Amazon ₹24,990, Croma ₹25,900, Vijay Sales ₹24,500 ...
  3. We extract the real retailer product URLs from each Shopping result
  4. Scrape each URL with universal_scraper.scrape_url() which handles ANY site
  5. Auto-detect Shopify / WooCommerce / HTML / JSON-LD on unknown sites
  6. Return results — new retailer works automatically, no code change needed

Why this is better than site_profiles.py alone:
  - site_profiles.py covers known retailers with tuned selectors (fast, accurate)
  - auto_discovery covers the long tail: Croma, Vijay Sales, Snapdeal, Paytm Mall,
    brand.com sites, regional retailers etc. without any config
  - Both run together — profiles win on speed, discovery wins on coverage

Requires: Playwright (for Google Shopping JS rendering)
Alternative: Google Shopping JSON API (unofficial) — faster but rate-limited
"""
import asyncio
import logging
import re
from typing import Optional
from urllib.parse import quote_plus, urlparse, unquote

from app.scrapers.base import BaseScraper, ScrapedPrice

logger = logging.getLogger(__name__)

# ── Domains to skip (aggregators, not actual retailers) ─────────────────────
SKIP_DOMAINS = {
    "google.com", "google.co.in",
    "youtube.com", "facebook.com", "twitter.com", "instagram.com",
    "wikipedia.org", "reddit.com", "quora.com",
    "justdial.com", "indiamart.com", "tradeindia.com",
    "pricespy.in", "91mobiles.com", "smartprix.com",
    "gsmarena.com", "gadgets360.com", "thewirecutter.com",
    "cashkaro.com", "coupondunia.in", "desidime.com",
    "jiocinema.com", "hotstar.com",
}

# ── Google Shopping URL patterns ────────────────────────────────────────────
GOOGLE_SHOPPING_URL    = "https://www.google.co.in/search?tbm=shop&q={query}&hl=en&gl=in"
GOOGLE_SHOPPING_URL_EN = "https://www.google.com/search?tbm=shop&q={query}&hl=en"


class AutoDiscovery(BaseScraper):
    """
    Discovers and scrapes new retailers automatically via Google Shopping.
    No manual site_profiles.py entry required for new retailers.
    """
    RETAILER_NAME = "AutoDiscovery"
    REQUEST_DELAY = 1.5

    # ── PUBLIC ────────────────────────────────────────────────────────────────

    async def search_and_discover(self, query: str, limit: int = 10) -> list[ScrapedPrice]:
        """
        Main entry point: search Google Shopping, get retailer URLs,
        scrape each one with universal scraper.

        Returns up to `limit` results from discovered retailers.
        Falls back to HTTP-only Google Shopping if Playwright fails.
        """
        logger.info(f"[AutoDiscover] Searching: '{query}'")

        # Step 1: Get retailer URLs from Google Shopping
        retailer_hits = await self._get_shopping_hits(query, limit * 2)

        if not retailer_hits:
            logger.warning("[AutoDiscover] No Google Shopping hits — trying HTTP fallback")
            retailer_hits = await self._get_shopping_hits_http(query, limit * 2)

        if not retailer_hits:
            logger.warning("[AutoDiscover] Could not get any Google Shopping results")
            return []

        logger.info(f"[AutoDiscover] Found {len(retailer_hits)} retailer URLs to scrape")

        # Step 2: Scrape each URL with universal scraper (handles any site)
        from app.scrapers.universal import universal_scraper
        tasks = [
            self._scrape_one(universal_scraper, hit["url"], hit.get("name"), hit.get("price"), hit.get("image"))
            for hit in retailer_hits[:limit]
        ]
        scraped = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for r in scraped:
            if isinstance(r, Exception):
                logger.debug(f"[AutoDiscover] Scrape error: {r}")
                continue
            if r and r.current_price:
                results.append(r)

        logger.info(f"[AutoDiscover] '{query}' → {len(results)} valid results from auto-discovery")
        return results

    # ── GOOGLE SHOPPING VIA PLAYWRIGHT ──────────────────────────────────────

    async def _get_shopping_hits(self, query: str, limit: int) -> list[dict]:
        """
        Scrape Google Shopping results page via Playwright.
        Extracts: retailer product URL, product name, price, image.
        """
        url  = GOOGLE_SHOPPING_URL.format(query=quote_plus(query))
        hits = []

        try:
            ctx  = await self._new_context()
            page = await ctx.new_page()

            # Set Indian locale to get correct prices/retailers
            await page.set_extra_http_headers({
                "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
            })

            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)

            # Try to find shopping result cards
            selectors = [
                "div.sh-dgr__grid-result",
                "div.sh-dlr__list-result",
                "div.KZmu8e",
                "div[data-docid]",
                "div.sh-pr__product-results li",
            ]
            items = []
            for sel in selectors:
                items = await page.query_selector_all(sel)
                if items:
                    logger.info(f"[AutoDiscover] Found {len(items)} cards with '{sel}'")
                    break

            for item in items[:limit]:
                try:
                    hit = await self._extract_shopping_card(item)
                    if hit:
                        hits.append(hit)
                except Exception as e:
                    logger.debug(f"[AutoDiscover] Card error: {e}")
                    continue

            await ctx.close()
        except Exception as e:
            logger.warning(f"[AutoDiscover] Playwright shopping failed: {e}")

        return hits

    async def _extract_shopping_card(self, item) -> Optional[dict]:
        """Extract product info from a single Google Shopping card element."""
        # ── Product URL ────────────────────────────────────────────────────
        link_el = (
            await item.query_selector("a[href*='/url?']") or
            await item.query_selector("a[href*='product']") or
            await item.query_selector("a.shntl") or
            await item.query_selector("a[data-merchant-url]") or
            await item.query_selector("a[href]")
        )
        if not link_el:
            return None

        href = await link_el.get_attribute("href") or ""
        product_url = self._resolve_google_url(href)
        if not product_url or self._should_skip(product_url):
            return None

        # ── Product Name ───────────────────────────────────────────────────
        name_el = (
            await item.query_selector("h3") or
            await item.query_selector("div.tAxDx") or
            await item.query_selector("h4") or
            await item.query_selector("[class*='title']")
        )
        name = (await name_el.inner_text()).strip() if name_el else ""

        # ── Price ──────────────────────────────────────────────────────────
        price_el = (
            await item.query_selector("span.a8Pemb") or
            await item.query_selector("span[data-price]") or
            await item.query_selector("span.HRLxBb") or
            await item.query_selector("[aria-label*='₹']") or
            await item.query_selector("[class*='price']")
        )
        price_raw = (await price_el.inner_text()).strip() if price_el else ""
        price = self.parse_price(price_raw)

        # ── Image ──────────────────────────────────────────────────────────
        img_el = await item.query_selector("img")
        img_src = None
        if img_el:
            img_src = await img_el.get_attribute("src")
            if img_src and ("data:image/gif" in img_src or "1x1" in img_src):
                img_src = await img_el.get_attribute("data-src") or None

        if not product_url:
            return None

        return {
            "url":   product_url,
            "name":  name,
            "price": price,
            "image": img_src,
        }

    # ── GOOGLE SHOPPING VIA HTTP (no Playwright) ─────────────────────────────

    async def _get_shopping_hits_http(self, query: str, limit: int) -> list[dict]:
        """
        HTTP fallback: fetch Google Shopping page without Playwright.
        Less reliable but works when Playwright is unavailable/slow.
        """
        from bs4 import BeautifulSoup
        from app.scrapers.smart_http import _fetch_curl_cffi, _fetch_urllib
        import asyncio as _a

        url  = GOOGLE_SHOPPING_URL.format(query=quote_plus(query))
        loop = _a.get_event_loop()
        html = await loop.run_in_executor(None, _fetch_curl_cffi, url, 12)
        if not html:
            html = await loop.run_in_executor(None, _fetch_urllib, url, 12)
        if not html:
            return []

        soup  = BeautifulSoup(html, "html.parser")
        hits  = []

        # Google Shopping HTML result cards
        for item in soup.select("div.sh-dgr__grid-result, div.sh-dlr__list-result, div[data-docid]")[:limit]:
            try:
                link = item.select_one("a[href]")
                if not link:
                    continue
                href = link.get("href", "")
                product_url = self._resolve_google_url(href)
                if not product_url or self._should_skip(product_url):
                    continue

                name_el  = item.select_one("h3, h4, .tAxDx")
                price_el = item.select_one("span.a8Pemb, span.HRLxBb, [class*='price']")
                img_el   = item.select_one("img")

                name  = name_el.get_text(strip=True)  if name_el  else ""
                price = self.parse_price(price_el.get_text(strip=True)) if price_el else None
                img   = img_el.get("src") or img_el.get("data-src") if img_el else None

                hits.append({"url": product_url, "name": name, "price": price, "image": img})
            except Exception:
                continue

        return hits

    # ── SCRAPE ONE RETAILER URL ───────────────────────────────────────────────

    async def _scrape_one(
        self,
        universal_scraper,
        url: str,
        hint_name:  Optional[str],
        hint_price,
        hint_image: Optional[str],
    ) -> Optional[ScrapedPrice]:
        """
        Scrape one retailer URL using universal scraper.
        If universal returns no price, fall back to Google Shopping's hint price
        so we at least show something.
        """
        try:
            result = await asyncio.wait_for(
                universal_scraper.scrape_url(url),
                timeout=12.0
            )

            # Fill in hints from Google Shopping if universal couldn't get them
            if result:
                if not result.current_price and hint_price:
                    result.current_price = hint_price
                    logger.info(f"[AutoDiscover] Used Google hint price ₹{hint_price} for {url[:50]}")
                if not result.product_name and hint_name:
                    result.product_name = hint_name
                if not result.image_url and hint_image:
                    result.image_url = hint_image
                if result.current_price:
                    return result

        except asyncio.TimeoutError:
            logger.debug(f"[AutoDiscover] Timeout scraping: {url[:60]}")
            # Return a minimal result using Google Shopping hints
            if hint_price and hint_name:
                domain = urlparse(url).netloc.replace("www.", "")
                return ScrapedPrice(
                    retailer=domain, url=url,
                    product_name=hint_name,
                    current_price=hint_price, mrp=None, discount_pct=None,
                    in_stock=True, image_url=hint_image,
                )
        except Exception as e:
            logger.debug(f"[AutoDiscover] Scrape failed {url[:50]}: {e}")

        return None

    # ── HELPERS ───────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_google_url(href: str) -> Optional[str]:
        """Convert Google redirect URL to real retailer URL."""
        if not href:
            return None
        # /url?q=https://retailer.com/... → https://retailer.com/...
        if "/url?" in href:
            m = re.search(r'[?&](?:q|url)=([^&]+)', href)
            if m:
                return unquote(m.group(1))
        # /shopping/product/... → Google Shopping page (skip)
        if href.startswith("/shopping"):
            return None
        # Relative → absolute
        if href.startswith("/"):
            return "https://www.google.co.in" + href
        return href if href.startswith("http") else None

    @staticmethod
    def _should_skip(url: str) -> bool:
        """Return True if this URL is not a real retailer (aggregator, social etc.)."""
        domain = urlparse(url).netloc.lower().replace("www.", "")
        return any(domain.endswith(skip) for skip in SKIP_DOMAINS)


# ── Singleton ─────────────────────────────────────────────────────────────────
auto_discovery = AutoDiscovery()
