"""
Google Shopping Scraper — DEVELOPMENT ONLY
===========================================
Scrapes google.com/search?tbm=shop using Playwright.

⚠️  Google's ToS prohibits automated scraping.
    Safe for development (< 50 searches/day).
    For production → switch to SerpApi ($50/mo) or Bing Shopping API ($3/1000).

Dev protections built in:
  - 1.5–3s random delay between requests (avoids rate limiting)
  - Warns in logs after 40 requests/day
  - Playwright full browser (harder to detect than urllib)
"""
import asyncio
import logging
import random
import time
from typing import Optional
from urllib.parse import quote_plus
import re
from decimal import Decimal

from app.scrapers.base import BaseScraper, ScrapedPrice

logger = logging.getLogger(__name__)

# Dev-mode request counter (in-memory, resets on restart)
_daily_request_count = 0
_DEV_WARN_THRESHOLD  = 40   # warn after this many in a session

class GoogleShoppingScraper(BaseScraper):
    RETAILER_NAME = "Google Shopping"
    BASE_URL      = "https://www.google.com/search?tbm=shop&q={query}"
    REQUEST_DELAY = 1.0

    async def scrape_url(self, url: str) -> ScrapedPrice:
        # Not applicable for URL scraping
        raise NotImplementedError

    async def search_product(self, query: str, limit: int = 10) -> list[ScrapedPrice]:
        global _daily_request_count
        _daily_request_count += 1
        if _daily_request_count >= _DEV_WARN_THRESHOLD:
            logger.warning(
                f"[Google Shopping] ⚠️  {_daily_request_count} requests this session. "
                f"Switch to SerpApi before going to production."
            )

        url = self.BASE_URL.format(query=quote_plus(query))
        logger.info(f"[Google Shopping] Searching: {query} (req #{_daily_request_count})")

        # Random delay: avoids triggering Google's rate limiter during dev
        await asyncio.sleep(random.uniform(1.5, 3.0))

        try:
            return await self.with_retry(self._search, url, limit)
        except Exception as e:
            logger.error(f"[Google Shopping] Search error: {e}")
            return []

    async def _search(self, url: str, limit: int) -> list[ScrapedPrice]:
        html, method, _ = await self.fetch_html_with_fallback(url)
        if not html:
            return []

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # ── Selector waterfall: try each set until we get items ──────────────
        # Google rotates class names frequently — we try 4 known patterns
        SELECTOR_SETS = [
            "div.sh-dgr__grid-result, div.sh-dlr__list-result",        # Standard grid
            "div.sh-pr__product-results div.KZmu8e",                    # Carousel / sponsored
            "div[data-docid]",                                          # Data attribute variant
            "div.g div.commercial-unit-desktop-rhs",                    # Right-hand shopping panel
        ]
        items = []
        for sel in SELECTOR_SETS:
            items = soup.select(sel)
            if items:
                logger.info(f"[Google Shopping] Matched {len(items)} cards via: {sel[:40]}")
                break

        if not items:
            logger.warning("[Google Shopping] All CSS selectors returned 0 items — trying JSON-LD fallback")
            # JSON-LD fallback: Google Shopping pages often embed structured product data
            jsonld_results = self.extract_jsonld_price(html)
            if jsonld_results.get("price") and jsonld_results.get("name"):
                from decimal import Decimal as D
                p = jsonld_results
                price = p.get("price")
                mrp   = None
                results.append(ScrapedPrice(
                    retailer="Google Shopping",
                    url=url,
                    product_name=p.get("name", ""),
                    current_price=price, mrp=mrp,
                    discount_pct=self.parse_discount(price, mrp),
                    in_stock=True,
                    image_url=p.get("image"),
                    brand=p.get("brand"),
                ))
                return results
        
            # Last resort: regex on raw HTML for ₹ prices + product names
            logger.warning("[Google Shopping] Falling back to regex price extraction")
            names  = re.findall(r'aria-label="([^"]{5,100})"', html)
            prices = re.findall(r'[₹\u20b9]\s*([\d,]+)', html)
            for i, (name, price_raw) in enumerate(zip(names[:limit], prices[:limit])):
                price = self.parse_price(price_raw)
                if price and name and price > 100:
                    results.append(ScrapedPrice(
                        retailer="Google Shopping",
                        url=url,
                        product_name=name,
                        current_price=price, mrp=None,
                        discount_pct=None, in_stock=True,
                    ))
            return results

        for item in items[:limit]:
            try:
                # Name — try multiple selectors
                name_el = (item.select_one("h3") or
                           item.select_one("div.tAxDx") or
                           item.select_one("h4") or
                           item.select_one("[aria-label]"))
                name = (name_el.get_text(strip=True) if name_el else
                        item.get("aria-label", ""))
                if not name:
                    continue

                # Category breadcrumb (optional)
                category_el = item.select_one("div.XPD7Et, div[data-category]")
                category = category_el.get_text(strip=True) if category_el else None

                # Price — try multiple selectors + regex fallback
                price_raw = ""
                price_el = (item.select_one("span.a8Pemb") or
                            item.select_one("span[data-price]") or
                            item.select_one("span.HRLxBb") or
                            item.select_one("[aria-label*='₹']") or
                            item.select_one("[aria-label*='Rs']"))
                if price_el:
                    price_raw = price_el.get_text(strip=True) or price_el.get("aria-label", "")
                if not price_raw:
                    # Regex fallback within this card's text
                    card_text = item.get_text()
                    m = re.search(r'[₹\u20b9]\s*([\d,]+)', card_text)
                    if m:
                        price_raw = m.group(1)

                # Retailer
                retailer_el = (item.select_one("div.aULzUe") or
                               item.select_one("div.IuHnof") or
                               item.select_one("div.b071yf") or
                               item.select_one("span.zPEcBd"))
                retailer_name = retailer_el.get_text(strip=True) if retailer_el else "Google Shopping"
                retailer_name = re.sub(r'\s*[·+·•].*', '', retailer_name).strip() or "Google Shopping"

                # Link
                product_url = ""
                link_el = (item.select_one("a[href*='/url?']") or
                           item.select_one("a[href*='/shopping/product']") or
                           item.select_one("a.shntl") or
                           item.select_one("a[href^='http']"))
                if link_el:
                    href = link_el.get("href", "")
                    if href.startswith("/url?"):
                        from urllib.parse import urlparse, parse_qs, unquote
                        try:
                            qs = parse_qs(urlparse(href).query)
                            product_url = unquote(qs.get('q', [''])[0])
                        except Exception:
                            product_url = ""
                    elif href.startswith("/shopping/product"):
                        product_url = "https://www.google.com" + href
                    elif href.startswith("http"):
                        product_url = href

                if not product_url:
                    continue

                # MRP
                mrp_raw = ""
                mrp_el = (item.select_one("span.aONvhf > span") or
                          item.select_one("span.KKh3md span:not(.a8Pemb)"))
                if mrp_el:
                    t = mrp_el.get_text(strip=True)
                    if re.search(r'\d', t):
                        mrp_raw = t

                # Image
                img_el = item.select_one("img")
                img_src = None
                if img_el:
                    img_src = img_el.get("src") or img_el.get("data-src")
                    if img_src and "data:image/gif" in img_src:
                        img_src = img_el.get("data-src")

                price = self.parse_price(price_raw)
                mrp   = self.parse_price(mrp_raw)
                if mrp and price and mrp <= price:
                    mrp = None

                if price and name:
                    results.append(ScrapedPrice(
                        retailer=retailer_name,
                        url=product_url,
                        product_name=name,
                        current_price=price, mrp=mrp,
                        discount_pct=self.parse_discount(price, mrp),
                        in_stock=True,
                        image_url=self.ensure_absolute_url(img_src, url) if img_src else None,
                    ))
            except Exception as e:
                logger.debug(f"[Google Shopping] Item parse error: {e}")
                continue

        return results
google_shopping_scraper = GoogleShoppingScraper()
