"""
Universal Product Scraper — Works for ANY website
==================================================
Anti-blocking strategy (5-layer waterfall):
  L0: Shopify/WooCommerce JSON API  — instant, no HTML parsing needed
  L1: SmartHTTP (urllib → curl_cffi → httpx → cloudscraper)
      Uses per-site profile to pick the right HTTP method first
  L2: JSON-LD / OpenGraph extraction from fetched HTML
  L3: Custom CSS selectors (per-site profile, then universal fallback)
  L4: Playwright (headless Chrome) for JS-rendered pages
  L5: Name-from-URL — always returns something, never crashes

Anti-blocking techniques used:
  ✅ Chrome-realistic User-Agents (rotated per request)
  ✅ Full sec-ch-ua + Accept-Language headers
  ✅ curl_cffi Chrome TLS fingerprint (beats most Cloudflare)
  ✅ HTTP/2 via httpx for modern sites
  ✅ Random request delay (0.5 - 2s)
  ✅ Per-site profile: right tool for right site first
  ✅ Playwright stealth mode for JS-only pages
  ✅ Shopify / WooCommerce API bypass (no HTML needed)
  ✅ JSON-LD structured data (most accurate price source)
  ✅ MRP range validation (reject EMI / bank-card prices)
  ✅ URL canonicalization (strip session tokens)
  ✅ Image: data-src lazy-load support
  ✅ Name: marketing junk stripped
"""
import asyncio
import logging
import os
import re
import tempfile
from decimal import Decimal
from typing import Optional
from urllib.parse import urlparse

from app.scrapers.base import BaseScraper, ScrapedPrice, get_browser
from app.scrapers.site_profiles import (
    SiteProfile, get_profile, detect_platform,
    TIER_1_URLLIB, TIER_2_CURL_CFFI, TIER_3_HTTPX,
    TIER_4_PLAYWRIGHT, TIER_SHOPIFY, TIER_WOOCOMMERCE,
)
from app.core.config import settings
from app.scrapers.identity_resolver import IdentityResolver

logger = logging.getLogger(__name__)

# ── Universal CSS selector pools (used when no site profile exists) ──────────
PRICE_SELECTORS = [
    "[itemprop='price']",
    "meta[property='product:price:amount']",
    ".price", ".product-price", ".sale-price", ".offer-price",
    ".selling-price", ".pdp-price", ".product__price",
    ".ProductPrice", "[class*='price'][class*='sale']",
    "[class*='selling-price']", "[class*='offer-price']",
    "[class*='discounted-price']", "[class*='final-price']",
    ".amount", "span.price", ".woocommerce-Price-amount",
    "[data-product-price]", "[data-price]", "#product-price",
    ".js-price-display", ".product-info-price .price",
]

MRP_SELECTORS = [
    ".compare-at-price", ".original-price", ".mrp", ".was-price",
    "[class*='compare']", "[class*='original-price']", "[class*='mrp']",
    "[class*='base-price']", "[class*='regular-price']",
    "s.price", "del .amount", ".line-through",
    "[data-compare-price]",
]

IMAGE_SELECTORS = [
    "[itemprop='image']", ".product-image img", ".pdp-image img",
    ".product__image img", ".gallery-image img",
    "[class*='product'][class*='image'] img",
    "[class*='ProductImage'] img", ".main-image img",
    "img[class*='product']", "img[class*='hero']",
    ".slick-active img", ".swiper-slide-active img",
    "figure.product img", "#product-image img",
]


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")


class UniversalScraper(BaseScraper):
    """
    Scrapes any product URL from any website.
    Uses per-site profiles for smart method selection.
    Falls back through 5 layers — never crashes.
    """
    RETAILER_NAME = "Universal"
    REQUEST_DELAY = 0.8

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC: scrape any URL
    # ─────────────────────────────────────────────────────────────────────────
    async def scrape_url(self, url: str) -> ScrapedPrice:
        clean_url = self.canonicalize_url(url, _domain(url))
        retailer  = _domain(clean_url)
        logger.info(f"[Universal] Scraping: {clean_url}")

        # Look up per-site profile
        profile = get_profile(clean_url)
        tier = profile.tier if profile else None

        # ── L0: Shopify JSON API ──────────────────────────────────────────
        # Works for: boAt, Mamaearth, Minimalist, Sugar, The Souled Store etc.
        is_shopify_site = (tier == TIER_SHOPIFY)
        if not is_shopify_site:
            # Auto-detect Shopify even for unregistered domains
            probe, _ = await self._safe_fetch(clean_url, TIER_1_URLLIB, timeout=6)
            if probe:
                detected = detect_platform(probe)
                if detected == TIER_SHOPIFY:
                    is_shopify_site = True
                elif detected == TIER_WOOCOMMERCE:
                    woo = await self._try_woocommerce_api(clean_url, retailer)
                    if woo and woo.current_price:
                        return woo
                elif probe:
                    # We already have the HTML — parse it directly (saves one round-trip)
                    result = self._parse_html(probe, clean_url, retailer, profile)
                    if result.current_price or result.product_name:
                        result = self._validate_and_clean(result, clean_url)
                        logger.info(f"[Universal] urllib parsed: {result.product_name[:50]} ₹{result.current_price}")
                        return result

        if is_shopify_site:
            shopify = await self._try_shopify_api(clean_url, retailer)
            if shopify and shopify.current_price:
                return shopify

        # ── L1: SmartHTTP waterfall (profile-aware) ───────────────────────
        # This now triggers the parallel race (urllib, curl_cffi, httpx)
        # plus ScraperAPI if the site is hard (Amazon, Flipkart etc.)
        html, method = await self._safe_fetch(clean_url, tier, retailer=retailer)
        if html and len(html) > 1000:
            result = self._parse_html(html, clean_url, retailer, profile)
            if result.current_price or result.product_name:
                result = self._validate_and_clean(result, clean_url)
                logger.info(f"[Universal] {method} parsed: {result.product_name[:50]} ₹{result.current_price}")
                return result

        # ── L2: Playwright (JS-rendered pages) ───────────────────────────
        logger.info(f"[Universal] Trying Playwright for: {clean_url}")
        try:
            pw = await self.with_retry(self._playwright_scrape, clean_url, retailer, profile)
            if pw and (pw.current_price or pw.product_name):
                return self._validate_and_clean(pw, clean_url)
        except Exception as e:
            logger.warning(f"[Universal] Playwright failed: {e}")

        # ── L3: Name from URL slug — always returns something ─────────────
        product_name = self._name_from_url(clean_url)
        logger.info(f"[Universal] L3 fallback — name from URL: {product_name}")
        return ScrapedPrice(
            retailer=retailer, url=clean_url,
            product_name=product_name,
            current_price=None, mrp=None, discount_pct=None,
            in_stock=True,
            error="Price requires JavaScript — site may be JS-only",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # TIER ORDER: which HTTP method to try first per site profile
    # ─────────────────────────────────────────────────────────────────────────
    def _tier_order(self, preferred: Optional[str]) -> list[str]:
        """Return fetch tier order, preferred tier first."""
        all_tiers = [TIER_1_URLLIB, TIER_2_CURL_CFFI, TIER_3_HTTPX]
        if preferred and preferred in all_tiers:
            rest = [t for t in all_tiers if t != preferred]
            return [preferred] + rest
        return all_tiers

    # ─────────────────────────────────────────────────────────────────────────
    # HTTP FETCH: routes to the correct library
    # ─────────────────────────────────────────────────────────────────────────
    async def _safe_fetch(self, url: str, tier: Optional[str] = None, retailer: str = "", timeout: int = 15) -> tuple[Optional[str], str]:
        """Run the universal smart_fetch (handles race + professional proxy)."""
        from app.scrapers.smart_http import smart_fetch
        try:
            # tier here is the "preferred" tier from site_profiles.py
            html, method, _ = await smart_fetch(
                url, 
                tier=tier or "urllib", 
                retailer=retailer, 
                timeout=timeout,
                playwright_scraper=self
            )
            return html, method
        except Exception as e:
            logger.debug(f"[Universal] smart_fetch failed: {e}")
            return None, "failed"

    # ─────────────────────────────────────────────────────────────────────────
    # HTML PARSER: all websites
    # ─────────────────────────────────────────────────────────────────────────
    def _parse_html(self, html: str, url: str, retailer: str, profile: Optional[SiteProfile] = None) -> ScrapedPrice:
        """
        Universal HTML parser. Extraction order:
          1. JSON-LD schema.org (most accurate — canonical price)
          2. Open Graph meta tags (og:price:amount)
          3. Per-site CSS selectors (from profile)
          4. Universal CSS selectors fallback
          5. Regex on raw HTML text (last resort)
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        name = price = mrp = image_url = brand = None

        # ── 1. JSON-LD (most authoritative price source) ──────────────────
        jsonld = self.extract_jsonld_price(html)
        if jsonld.get("price"):
            price = jsonld["price"]
        if jsonld.get("name"):
            name = jsonld["name"]
        if jsonld.get("image"):
            image_url = jsonld["image"]
        if jsonld.get("brand"):
            brand = jsonld["brand"]

        # ── 2. Open Graph meta tags ───────────────────────────────────────
        def og(prop: str) -> Optional[str]:
            el = (soup.find("meta", property=prop) or
                  soup.find("meta", attrs={"name": prop}))
            return el.get("content", "").strip() if el else None

        if not image_url:
            image_url = og("og:image") or og("twitter:image")
            if image_url:
                image_url = self.ensure_absolute_url(image_url, url)
        if not price:
            raw = og("og:price:amount") or og("product:price:amount") or og("twitter:data1")
            if raw:
                price = self.parse_price(raw)
        if not mrp:
            raw = og("og:original_price:amount") or og("product:original_price:amount")
            if raw:
                mrp_c = self.parse_price(raw)
                if mrp_c and price and mrp_c > price:
                    mrp = mrp_c

        # ── 3. CSS selectors (site-specific first, then universal) ────────
        price_sels = (profile.price_selectors if profile else []) + PRICE_SELECTORS
        mrp_sels   = (profile.mrp_selectors   if profile else []) + MRP_SELECTORS
        name_sels  = (profile.name_selectors  if profile else [])
        image_sels = (profile.image_selectors if profile else []) + IMAGE_SELECTORS

        # ── 3.1: Member/Prime prices ──────────────────────────────────────
        if not price and profile:
            for sel in profile.member_price_selectors:
                el = soup.select_one(sel)
                if el:
                    val = el.get_text(strip=True) or el.get("content", "")
                    p = self.parse_price(val)
                    if p and p > 0:
                        price = p
                        metadata["is_member"] = True
                        logger.info(f"[{retailer}] Found member/prime price: ₹{price}")
                        break

        # ── 3.2: Login Required Detection ─────────────────────────────────
        requires_login = False
        if profile:
            for sel in profile.login_required_selectors:
                if soup.select_one(sel):
                    requires_login = True
                    metadata["requires_login"] = True
                    logger.info(f"[{retailer}] Login required to see price.")
                    break

        if not price:
            for sel in price_sels:
                el = soup.select_ones(sel) if hasattr(soup, 'select_ones') else soup.select_one(sel)
                if el:
                    p_c = self.parse_price(el.get_text(strip=True))
                    if p_c:
                        price = p_c
                        break
                    el = soup.select_one(sel)
                    if el:
                        val = (el.get_text(strip=True) or
                               el.get("content", "") or
                               el.get("data-price", ""))
                        p = self.parse_price(val)
                        if p and p > 0:
                            price = p
                            break

        if not mrp:
            for sel in mrp_sels:
                el = soup.select_one(sel)
                if el:
                    m = self.parse_price(el.get_text(strip=True))
                    if m and price and m > price:
                        mrp = m
                        break

        # ── 3.3: Login Required check ─────────────────────────────────────
        requires_login = False
        if profile and profile.login_required_selectors:
            for sel in profile.login_required_selectors:
                if soup.select_one(sel):
                    requires_login = True
                    break
        metadata["requires_login"] = requires_login

        if not name:
            for sel in name_sels + ["h1", "h1[itemprop='name']"]:
                el = soup.select_one(sel)
                if el:
                    name = el.get_text(strip=True)
                    if name:
                        break

        if not image_url:
            for sel in image_sels:
                el = soup.select_one(sel)
                if el:
                    src = (el.get("src") or el.get("data-src") or
                           el.get("data-lazy-src") or el.get("content"))
                    if src and "placeholder" not in src:
                        image_url = self.ensure_absolute_url(src, url)
                        break

        # ── 4. Fallback: h1 or <title> for name ──────────────────────────
        if not name:
            h1 = soup.find("h1")
            name = (h1.get_text(strip=True) if h1 else
                    (soup.title.string.strip() if soup.title else ""))

        # ── 5. Regex on raw HTML as absolute last resort for price ────────
        if not price:
            rupees = re.findall(r'[\u20b9][\s]*([0-9,]{2,8})', html)
            rs     = re.findall(r'Rs\.?\s*([0-9,]{2,8})', html)
            both   = [int(p.replace(",", "")) for p in (rupees + rs)]
            valid  = [p for p in both if 50 <= p <= 5_000_000]
            if valid:
                price = self.parse_price(str(min(valid)))

        # ── Clean up name ─────────────────────────────────────────────────
        if name:
            name = re.sub(
                r"\s*[-|–|•]\s*.*(shop|store|buy|india|\.com|\.in|official|™|®).*",
                "", name, flags=re.IGNORECASE
            ).strip()
            name = self.clean_name(name)

        # ── Stock check ───────────────────────────────────────────────────
        text_lower = soup.get_text().lower()
        in_stock = not any(p in text_lower for p in [
            "out of stock", "sold out", "currently unavailable",
            "notify me when available", "coming soon",
        ])

        if mrp and price and mrp <= price:
            mrp = None

        return ScrapedPrice(
            retailer=retailer, url=url,
            product_name=name or "",
            current_price=price, mrp=mrp,
            discount_pct=self.parse_discount(price, mrp),
            in_stock=in_stock, image_url=image_url or None,
            brand=brand or (name.split()[0] if name else None),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # VALIDATE & CLEAN: apply all Issue 2+3 fixes
    # ─────────────────────────────────────────────────────────────────────────
    def _validate_and_clean(self, result: ScrapedPrice, url: str) -> ScrapedPrice:
        """Apply price validation, name cleaning, and URL canonicalization."""
        # Validate price against MRP range
        result.current_price = self.validate_price(result.current_price, result.mrp)
        # Clean product name
        if result.product_name:
            result.product_name = self.clean_name(result.product_name)
        # Canonicalize URL
        result.url = self.canonicalize_url(url, _domain(url))
        # Recalculate discount
        result.discount_pct = self.parse_discount(result.current_price, result.mrp)
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # SHOPIFY API
    # ─────────────────────────────────────────────────────────────────────────
    async def _try_shopify_api(self, url: str, retailer: str) -> Optional[ScrapedPrice]:
        """
        Shopify /products/[handle].json API.
        Works for: boAt, Mamaearth, Minimalist, Sugar, The Souled Store + 1000s more.
        Most accurate price — straight from the inventory system.
        """
        import json as _json
        parsed = urlparse(url)
        base   = f"{parsed.scheme}://{parsed.netloc}"
        handle_m = re.search(r'/products?/([^/?#]+)', parsed.path)
        if not handle_m:
            return None

        handle  = handle_m.group(1)
        api_url = f"{base}/products/{handle}.json"
        html, _ = await self._safe_fetch(api_url, TIER_1_URLLIB, timeout=8)
        if not html or len(html) < 50:
            return None

        try:
            data    = _json.loads(html)
            product = data.get("product", data)
            name    = product.get("title", "")
            vendor  = product.get("vendor", "")
            variants = product.get("variants", [])
            if not variants:
                return None

            in_stock_vars = [v for v in variants if v.get("available") is not False]
            target  = in_stock_vars[0] if in_stock_vars else variants[0]
            price   = self.parse_price(str(target.get("price", "0")).split(".")[0])
            cmp_raw = str(target.get("compare_at_price") or "")
            mrp     = self.parse_price(cmp_raw.split(".")[0]) if cmp_raw and cmp_raw != "0" else None
            if mrp and price and mrp <= price:
                mrp = None

            images  = product.get("images", [])
            img_url = images[0].get("src") if images else None
            in_stock = any(v.get("available") is not False for v in variants)

            full_name = f"{vendor} {name}".strip() if vendor and vendor.lower() not in name.lower() else name
            logger.info(f"[Universal] Shopify API ✅ {full_name} ₹{price}")
            return ScrapedPrice(
                retailer=retailer, url=url,
                product_name=self.clean_name(full_name),
                current_price=self.validate_price(price, mrp),
                mrp=mrp,
                discount_pct=self.parse_discount(price, mrp),
                in_stock=in_stock, image_url=img_url,
                brand=vendor or (name.split()[0] if name else None),
            )
        except Exception as e:
            logger.debug(f"[Universal] Shopify parse failed: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # WOOCOMMERCE API
    # ─────────────────────────────────────────────────────────────────────────
    async def _try_woocommerce_api(self, url: str, retailer: str) -> Optional[ScrapedPrice]:
        """
        WooCommerce REST API: /wp-json/wc/v3/products?slug=[slug]
        Works for many Indian brand websites built on WordPress + WooCommerce.
        """
        import json as _json
        parsed = urlparse(url)
        base   = f"{parsed.scheme}://{parsed.netloc}"
        slug   = parsed.path.rstrip("/").split("/")[-1]
        api_url = f"{base}/wp-json/wc/store/products?slug={slug}"
        html, _ = await self._safe_fetch(api_url, TIER_1_URLLIB, timeout=8)
        if not html:
            return None
        try:
            items = _json.loads(html)
            if not items:
                return None
            p = items[0]
            name  = p.get("name", "")
            price_raw = p.get("prices", {}).get("price", "")
            mrp_raw   = p.get("prices", {}).get("regular_price", "")
            # WooCommerce prices are in minor units (paise) sometimes
            price = self.parse_price(str(int(price_raw) // 100 if int(price_raw or 0) > 100000 else price_raw))
            mrp   = self.parse_price(str(int(mrp_raw) // 100 if int(mrp_raw or 0) > 100000 else mrp_raw))
            if mrp and price and mrp <= price:
                mrp = None
            img_url = (p.get("images") or [{}])[0].get("src")
            in_stock = p.get("is_in_stock", True)
            logger.info(f"[Universal] WooCommerce API ✅ {name} ₹{price}")
            return ScrapedPrice(
                retailer=retailer, url=url,
                product_name=self.clean_name(name),
                current_price=self.validate_price(price, mrp),
                mrp=mrp,
                discount_pct=self.parse_discount(price, mrp),
                in_stock=in_stock, image_url=img_url,
                brand=name.split()[0] if name else None,
            )
        except Exception as e:
            logger.debug(f"[Universal] WooCommerce parse failed: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # PLAYWRIGHT: headless Chrome for JS-heavy pages
    # ─────────────────────────────────────────────────────────────────────────
    async def _playwright_scrape(self, url: str, retailer: str, profile: Optional[SiteProfile] = None) -> ScrapedPrice:
        """
        Full Playwright scrape with stealth mode.
<<<<<<< HEAD
        Used as last resort for heavy JS pages (JS-rendered prices/images).
        """
        try:
            wait_sel = (profile.wait_selector if profile else None) or "body"
            page = await self._get_page(url, wait_selector=wait_sel)
            try:
                # Wait a bit extra for JS price rendering
                await page.wait_for_timeout(2000)

                # Get rendered HTML and parse it
                html = await page.content()
                result = self._parse_html(html, url, retailer, profile)
                if result.current_price:
                    return result

                # If still no price, try Playwright-based element extraction
                price_sels = (profile.price_selectors if profile else []) + PRICE_SELECTORS
                for sel in price_sels:
                    val = await self._pw_text(page, sel)
                    if val and re.search(r'\d', val):
                        p = self.parse_price(val)
                        if p and p > 0:
                            result.current_price = p
                            break

                if not result.image_url:
                    image_sels = (profile.image_selectors if profile else []) + IMAGE_SELECTORS
                    for sel in image_sels:
                        img = (await self._pw_attr(page, sel, "src") or
                               await self._pw_attr(page, sel, "data-src"))
                        if img and img.startswith("http"):
                            result.image_url = img
                            break

                return result
            finally:
                if page:
                    await page.context.close()
                    await page.close()
        except Exception as e:
            logger.error(f"[Universal] Playwright scrape failed for {url}: {e}")
            # Return an empty result with the error rather than crashing
            return ScrapedPrice(retailer=retailer, url=url, product_name="", current_price=None, mrp=None, discount_pct=None, error=str(e))

=======
        Used as last resort for heavy JS pages (Meesho, Tanishq etc.)
        """
        wait_sel = (profile.wait_selector if profile else None) or "body"
        page = await self._get_page(url, wait_selector=wait_sel)
        try:
            # Wait a bit extra for JS price rendering
            await page.wait_for_timeout(2000)

            # Get rendered HTML and parse it
            html = await page.content()
            result = self._parse_html(html, url, retailer, profile)
            if result.current_price:
                return result

            # If still no price, try Playwright-based element extraction
            # (JS may have rendered it into elements not in initial HTML)
            price_sels = (profile.price_selectors if profile else []) + PRICE_SELECTORS
            for sel in price_sels:
                val = await self._pw_text(page, sel)
                if val and re.search(r'\d', val):
                    p = self.parse_price(val)
                    if p and p > 0:
                        result.current_price = p
                        break

            if not result.image_url:
                image_sels = (profile.image_selectors if profile else []) + IMAGE_SELECTORS
                for sel in image_sels:
                    img = (await self._pw_attr(page, sel, "src") or
                           await self._pw_attr(page, sel, "data-src"))
                    if img and img.startswith("http"):
                        result.image_url = img
                        break

            return result
        finally:
            await page.context.close()
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3

    # ─────────────────────────────────────────────────────────────────────────
    # TEXT SEARCH — profile-driven, all retailers in parallel
    # ─────────────────────────────────────────────────────────────────────────
<<<<<<< HEAD
    async def search_by_name(self, query: str, limit_per_site: int = 5, user_category: Optional[str] = None, allowed_retailers: Optional[list[str]] = None) -> dict:
=======
    async def search_by_name(self, query: str, limit_per_site: int = 5, user_category: Optional[str] = None) -> dict:
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
        """
        Deltadrop Identity & Discovery (DID) Engine.
        1. Resolve Identity via Google.
        2. Discover retailers via Google Shopping.
        3. Scrape live prices.
        4. Guard against replicas.
        5. Filter by category (if specified).
        """
        from app.scrapers.site_profiles import get_searchable_profiles
        from app.scrapers.google_shopping import google_shopping_scraper
        from app.scrapers.category_router import (
            get_relevant_retailers, extract_specs, detect_category, build_variant_query
        )


        # ── STEP 1: IDENTITY RESOLUTION ───────────────────────────────────────
        resolver = IdentityResolver(self)
        identity = await resolver.resolve(query)
        canonical_name = identity["canonical_name"] or query
        resolved_msrp  = identity.get("msrp_estimate")
        google_cat     = identity.get("category")

        logger.info(f"[DID] Resolved Identity: '{canonical_name}' | Cat: {google_cat} | MSRP: {resolved_msrp}")

        # Specs for internal metadata
        specs = extract_specs(canonical_name)
        search_query = build_variant_query(canonical_name, specs) if not specs.is_empty() else canonical_name

        # ── STEP 2: MULTI-ENGINE DISCOVERY ────────────────────────────────────
        
        # A: Google Shopping — primary universal discovery
        google_task = google_shopping_scraper.search_product(search_query, limit=15)

        # B: Profile-driven backup
        all_profiles = get_searchable_profiles()
        filtered_profiles, brand_urls = get_relevant_retailers(canonical_name, all_profiles)
<<<<<<< HEAD
        from app.scrapers.search_optimizer import search_optimizer
        
        scrape_profiles = []
        for p in filtered_profiles:
            if allowed_retailers:
                retailer_matches = False
                for allowed in allowed_retailers:
                    if search_optimizer._source_matches_retailer(allowed, p.domain):
                        retailer_matches = True
                        break
                if not retailer_matches:
                    logger.debug(f"[Universal] Skipping blocked retailer profile: {p.domain}")
                    continue
            scrape_profiles.append(p)
=======
        scrape_profiles = [
            p for p in filtered_profiles
            # if not (amazon_paapi.is_available and "amazon" in p.domain)
        ]
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
        profile_task = asyncio.gather(
            *[self._search_one_site(search_query, p, limit_per_site) for p in scrape_profiles],
            return_exceptions=True
        )

        # C: Amazon PA-API (Disabled as module is missing)
        paapi_task = asyncio.sleep(0.01) # Mock task returning nothing

        # D: Brand website
        brand_tasks = [
            asyncio.wait_for(self.scrape_url(burl), timeout=12.0)
            for burl in brand_urls
        ]

        all_gathered = await asyncio.gather(
            google_task, profile_task, paapi_task, *brand_tasks,
            return_exceptions=True
        )

        google_results  = all_gathered[0] if isinstance(all_gathered[0], list) else []
        profile_batches = all_gathered[1]
        paapi_results   = all_gathered[2] if isinstance(all_gathered[2], list) else []
        brand_raw       = all_gathered[3:]
        brand_results   = [r for r in brand_raw if isinstance(r, ScrapedPrice) and r.current_price]

        # ── STEP 3: CONFIRM LIVE PRICES ───────────────────────────────────────
        live_tasks = [
            asyncio.wait_for(self._confirm_live_price(gr), timeout=12.0)
            for gr in google_results
            if gr.url and gr.url.startswith("http")
        ]
        live_confirmed = [r for r in await asyncio.gather(*live_tasks, return_exceptions=True) if isinstance(r, ScrapedPrice)]

        # Merge results
        results = live_confirmed + paapi_results + brand_results
        if isinstance(profile_batches, list):
            for batch in profile_batches:
                if isinstance(batch, list): results.extend(batch)

        results = self._deduplicate_by_domain(results)

        # ── Step 4: APPLY SMART RELEVANCE & ORIGINALITY FILTER ────────────────
        EXACT_THRESHOLD = 0.45
        CLOSE_THRESHOLD = 0.15
        REPLICA_THRESHOLD = 0.40  # Flag if price < 40% of MSRP for high-end items

        final_results = []
        for r in results:
            if not r.product_name:
                continue

            score = self.calculate_relevance(query, r.product_name, retailer=r.retailer, url=r.url)
            
            # Originality Guard: Filter out suspected replicas
            is_replica = False
            if resolved_msrp and r.current_price:
                # If price is suspiciously low (e.g. ₹2000 for ₹20000 shoes)
                if r.current_price < (Decimal(str(resolved_msrp)) * Decimal(str(REPLICA_THRESHOLD))):
                    is_replica = True
                    logger.warning(f"[OriginalityGuard] Flagged replica: '{r.product_name}' at ₹{r.current_price} vs MSRP ₹{resolved_msrp}")

            if score >= CLOSE_THRESHOLD and not is_replica:
                # ── Category Guard: Filter if user specified a category ───────
                if user_category:
                    # Heuristic: does the result name or category contains the user's category?
                    # e.g. "Shoes" in "Sneakers > Sports Shoes"
                    r_cat = (getattr(r, 'category', '') or '').lower()
                    u_cat = user_category.lower()
                    if u_cat not in r_cat and u_cat not in r.product_name.lower():
                        logger.debug(f"[CategoryGuard] Rejected '{r.product_name}' - doesn't match '{user_category}'")
                        continue

                r.relevance_score = score
                r.is_close_match = score < EXACT_THRESHOLD
                final_results.append(r)
            elif is_replica:
                logger.debug(f"[OriginalityGuard] Rejected '{r.product_name}' (suspected replica)")
            else:
                logger.debug(f"[SmartFilter] Rejected '{r.product_name}' (low score {score:.2f})")

        # Sort: exact first, then close matches, then price descending within tiers
        final_results.sort(
            key=lambda x: (x.is_close_match, -x.relevance_score, x.current_price or 999999)
        )

        # ── STEP 5: DIAGNOSIS IF 0 RESULTS ────────────────────────────────────
        diagnosis = None
        if not final_results:
            if results:
                diagnosis = (
                    f"We found {len(results)} potential matches, but they were filtered out "
                    f"because they appeared to be replicas or didn't match the '{canonical_name}' identity."
                )
            else:
                diagnosis = (
                    f"No verified retailers found for '{canonical_name}'. "
                    "The item might be out of stock, or your search might be too specific."
                )

        return {
            "results":  final_results,
            "specs":    specs.to_dict(),
            "category": google_cat or identity.get("category"),
            "diagnosis": diagnosis,
            "identity": {
                "name": canonical_name,
                "brand": identity.get("brand"),
                "msrp": resolved_msrp
            }
        }

        # Merge live prices back — keep Google's image/name, replace price with live
        from urllib.parse import urlparse
        google_map: dict[str, ScrapedPrice] = {}
        for gr in google_results:
            domain = urlparse(gr.url).netloc.replace("www.", "") if gr.url else gr.retailer
            google_map[domain] = gr
        for lr in live_confirmed:
            domain = urlparse(lr.url).netloc.replace("www.", "") if lr.url else lr.retailer
            if domain in google_map:
                gbase            = google_map[domain]
                lr.image_url     = lr.image_url    or gbase.image_url
                lr.product_name  = lr.product_name or gbase.product_name
                google_map[domain] = lr

        # ── Assemble final results ────────────────────────────────────────────
        results = list(google_map.values())   # Google (live-confirmed, most relevant)
        results.extend(paapi_results)

        if isinstance(profile_batches, list):
            for batch in profile_batches:
                if isinstance(batch, list):
                    results.extend(batch)

        results.extend(brand_results)
        results = self._deduplicate_by_domain(results)

        # ── Step 3: APPLY SMART RELEVANCE FILTER ──────────────────────────────
        # Reject fakes, wrong brands, and junk. Threshold 0.3 for discovery.
        filtered_results = []
        for r in results:
            if not r.product_name:
                continue
                
            score = self.calculate_relevance(query, r.product_name, retailer=r.retailer, url=r.url)
            
            if score >= 0.15:
                r.relevance_score = score
                filtered_results.append(r)
            else:
                logger.debug(f"[SmartFilter] Rejected '{r.product_name}' (score {score:.2f})")

        # Final Sort: Brand Site > Higher Relevance > Best Price
        filtered_results.sort(key=lambda x: (x.relevance_score, -x.current_price or 0), reverse=True)

        logger.info(
            f"[Universal] Final: {len(filtered_results)} results for '{query}' "
            f"(Filtered from {len(results)})"
        )

        return {
            "results":  filtered_results,
            "specs":    specs.to_dict(),
            "category": category,
        }

    async def _confirm_live_price(self, google_result: ScrapedPrice) -> ScrapedPrice:
        """
        Scrape the Google-discovered URL for live current price/stock/discount.
        Falls back to the original Google-cached result if scraping fails.
        This guarantees we always show something even if the scraper is blocked.
        """
        try:
            live = await self.scrape_url(google_result.url)
            if live and live.current_price:
                live.image_url    = live.image_url    or google_result.image_url
                live.product_name = live.product_name or google_result.product_name
                live.retailer     = live.retailer     or google_result.retailer
                return live
        except Exception:
            pass
        return google_result   # scrape failed — use Google cached price


    def _deduplicate_by_domain(self, results: list[ScrapedPrice]) -> list[ScrapedPrice]:
        """
        If two results are from the same domain (e.g., both amazon.in),
        keep whichever has more complete data (price + name wins over name-only).
        Prevents showing the same retailer twice in the comparison table.
        """
        domain_best: dict[str, ScrapedPrice] = {}
        for r in results:
            domain = urlparse(r.url).netloc.lower().replace("www.", "") if r.url else r.retailer
            existing = domain_best.get(domain)
            if existing is None:
                domain_best[domain] = r
            else:
                # Prefer whichever has a price; if both have price, prefer lower
                if r.current_price and (
                    not existing.current_price or
                    r.current_price < existing.current_price
                ):
                    domain_best[domain] = r
        return list(domain_best.values())


    async def _search_one_site(self, query: str, profile: "SiteProfile", limit: int = 5) -> list[ScrapedPrice]:
        """
        Search one retailer using its profile config.
        Handles three search types:
          html          → fetch HTML, parse product cards
          json_api      → call JSON REST API, extract from structured response
          embedded_json → fetch HTML, extract JSON blob via regex
        """
        import asyncio as _asyncio
        try:
            return await _asyncio.wait_for(
                self._search_one_site_inner(query, profile, limit),
                timeout=35.0
            )
        except _asyncio.TimeoutError:
            logger.warning(f"[{profile.domain}] Search timeout")
            return []
        except Exception as e:
            logger.warning(f"[{profile.domain}] Search error: {e}")
            return []

    async def _search_one_site_inner(self, query: str, profile: "SiteProfile", limit: int) -> list[ScrapedPrice]:
        from urllib.parse import quote_plus
        retailer = profile.domain

        # ── JSON API ─────────────────────────────────────────────────────────
        if profile.search_type == "json_api" and profile.search_api_url:
            url  = profile.search_api_url.replace("{query}", quote_plus(query))
            html, method, total_ms = await self.fetch_html_with_fallback(url)
            if html:
                results = self._parse_json_api_results(html, profile, retailer, limit)
                if results:
                    logger.info(f"[{retailer}] JSON API found {len(results)} via {method}")
                    return [self._clean(r) for r in results]

        # ── Embedded JSON (Flipkart, Myntra) ─────────────────────────────────
        elif profile.search_type == "embedded_json":
            url = self._build_search_url(query, profile)
            html, method, total_ms = await self.fetch_html_with_fallback(url)
            if html:
                results = self._parse_embedded_json_results(html, profile, retailer, limit)
                if results:
                    logger.info(f"[{retailer}] Embedded JSON found {len(results)} via {method}")
                    return [self._clean(r) for r in results]

        # ── HTML card parsing (Amazon) ────────────────────────────────────────
        elif profile.search_type == "html" and profile.search_url:
            url = self._build_search_url(query, profile)
            html, method, total_ms = await self.fetch_html_with_fallback(url)
            if html:
                results = self._parse_html_search_results(html, profile, retailer, limit)
                if results:
                    logger.info(f"[{retailer}] HTML search found {len(results)} via {method}")
                    return [self._clean(r) for r in results]

        return []

    def _build_search_url(self, query: str, profile: "SiteProfile") -> str:
        """Build search URL from profile template."""
        from urllib.parse import quote_plus
        base = profile.search_url or profile.search_api_url or ""
        slug = query.lower().replace(" ", "-")
        return (
            base
            .replace("{query}", quote_plus(query))
            .replace("{query_slug}", quote_plus(slug))
        )

    def _parse_json_api_results(self, text: str, profile: "SiteProfile", retailer: str, limit: int) -> list[ScrapedPrice]:
        """Parse JSON API response using profile field mappings."""
        import json as _json
        from app.scrapers.site_profiles import resolve_json_path
        try:
            data = _json.loads(text)
        except Exception:
            return []

        # Navigate to products list using dot-separated path
        products = resolve_json_path(data, profile.json_products_path) or []
        if not isinstance(products, list):
            return []

        results = []
        for p in products[:limit]:
            try:
                name  = resolve_json_path(p, profile.json_name_key) or ""
                price_raw = resolve_json_path(p, profile.json_price_key)
                mrp_raw   = resolve_json_path(p, profile.json_mrp_key)
                url_raw   = resolve_json_path(p, profile.json_url_key) or ""
                img_raw   = resolve_json_path(p, profile.json_image_key)
                brand_raw = resolve_json_path(p, profile.json_brand_key)

                price = self.parse_price(str(price_raw)) if price_raw else None
                mrp   = self.parse_price(str(mrp_raw))   if mrp_raw  else None
                if mrp and price and mrp <= price:
                    mrp = None

                # Build full URL
                url = str(url_raw)
                if url and not url.startswith("http"):
                    url = profile.json_url_prefix.rstrip("/") + "/" + url.lstrip("/")

                if price and price > 0 and name:
                    results.append(ScrapedPrice(
                        retailer=retailer, url=url or f"https://{retailer}",
                        product_name=name,
                        current_price=price, mrp=mrp,
                        discount_pct=self.parse_discount(price, mrp),
                        in_stock=True,
                        image_url=self.ensure_absolute_url(str(img_raw), url) if img_raw else None,
                        brand=str(brand_raw) if brand_raw else name.split()[0],
                    ))
            except Exception as e:
                logger.debug(f"[{retailer}] JSON item parse error: {e}")
                continue
        return results

    def _parse_html_search_results(self, html: str, profile: "SiteProfile", retailer: str, limit: int) -> list[ScrapedPrice]:
        """Parse HTML search result page using profile CSS selectors."""
        from bs4 import BeautifulSoup
        soup    = BeautifulSoup(html, "html.parser")
        results = []

        container_sel = profile.result_container_sel or "article, .product-card, li[class*='product']"
        cards = soup.select(container_sel)

        for card in cards[:limit]:
            try:
                # Name
                name_el = card.select_one(profile.result_name_sel or "h2")
                name    = name_el.get_text(strip=True) if name_el else ""

                # Price
                price_el  = card.select_one(profile.result_price_sel or ".price")
                price_raw = price_el.get_text(strip=True) if price_el else ""
                price     = self.parse_price(price_raw)

                # MRP
                mrp_el  = card.select_one(profile.result_mrp_sel or ".original-price") if profile.result_mrp_sel else None
                mrp_raw = mrp_el.get_text(strip=True) if mrp_el else ""
                mrp     = self.parse_price(mrp_raw)
                if mrp and price and mrp <= price:
                    mrp = None

                # URL
                link_el = card.select_one(profile.result_link_sel or "a[href]")
                href    = link_el.get("href", "") if link_el else ""
                url     = self.ensure_absolute_url(href, f"https://{retailer}")
                url     = self.canonicalize_url(url, retailer)

                # Image (prefer data-src for lazy-loaded)
                img_el  = card.select_one(profile.result_image_sel or "img")
                img_src = None
                if img_el:
                    img_src = (img_el.get("src") or img_el.get("data-src") or img_el.get("data-lazy-src"))
                    if img_src and "placeholder" in img_src:
                        img_src = img_el.get("data-src")

                if price and price > 0 and name and url:
                   results.append(ScrapedPrice(
                        retailer=retailer, url=url,
                        product_name=name,
                        current_price=price, mrp=mrp,
                        discount_pct=self.parse_discount(price, mrp),
                        in_stock=True, 
                        image_url=self.ensure_absolute_url(img_src, f"https://{retailer}") if img_src else None,
                        brand=name.split()[0] if name else None,
                    ))
            except Exception as e:
                logger.debug(f"[{retailer}] HTML card parse error: {e}")
                continue
        return results

    def _parse_embedded_json_results(self, html: str, profile: "SiteProfile", retailer: str, limit: int) -> list[ScrapedPrice]:
        """
        Parse search results where product data is embedded in page HTML
        as a JSON blob inside a <script> tag (Myntra, Flipkart).
        Falls back to HTML card parsing if JSON extraction fails.
        """
        # ── Myntra: extract via regex on inline JS ────────────────────────────
        if "myntra.com" in retailer:
            return self._parse_myntra_embedded(html, retailer, limit)

        # ── Flipkart: extract from window.__INITIAL_STATE__ ───────────────────
        if "flipkart.com" in retailer:
            return self._parse_flipkart_embedded(html, retailer, limit)

        # ── Generic: try CSS selectors as fallback ────────────────────────────
        return self._parse_html_search_results(html, profile, retailer, limit)

    def _parse_myntra_embedded(self, html: str, retailer: str, limit: int) -> list[ScrapedPrice]:
        """Extract Myntra products from embedded JS data via regex."""
        import re
        results = []
        ids    = re.findall(r'"productId"\s*:\s*(\d+)', html)
        names  = re.findall(r'"productName"\s*:\s*"([^"]{5,120})"', html)
        prices = re.findall(r'"discountedPrice"\s*:\s*(\d+)', html)
        mrps   = re.findall(r'(?<!")"price"\s*:\s*(\d+)', html)
        imgs   = re.findall(r'(https://assets\.myntassets\.com/[^\s"]+\.(?:jpg|jpeg|webp))', html)

        for i in range(min(limit, len(ids), len(names), len(prices))):
            try:
                from decimal import Decimal as D
                price = D(prices[i])
                mrp   = D(mrps[i]) if i < len(mrps) and int(mrps[i]) > int(price) else None
                results.append(ScrapedPrice(
                    retailer=retailer,
                    url=f"https://www.myntra.com/{ids[i]}",
                    product_name=names[i],
                    current_price=price, mrp=mrp,
                    discount_pct=self.parse_discount(price, mrp),
                    in_stock=True,
                    image_url=imgs[i] if i < len(imgs) else None,
                    brand=names[i].split()[0] if names[i] else None,
                ))
            except Exception:
                continue
        return results

    def _parse_flipkart_embedded(self, html: str, retailer: str, limit: int) -> list[ScrapedPrice]:
        """Extract Flipkart products from embedded __INITIAL_STATE__ JSON."""
        import re, json as _json
        from decimal import Decimal as D

        results  = []
        # Try to find the JSON blob
        pattern  = r'window\.__INITIAL_STATE__\s*=\s*(\{.*?"pageData".*?\});'
        match    = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                state  = _json.loads(match.group(1))
                # Flatten all product objects from the deeply nested state
                raw    = _json.dumps(state)
                names  = re.findall(r'"title"\s*:\s*"([^"]{5,120})"', raw)
                prices = re.findall(r'"sellingPrice"\s*:\s*(\d+)', raw)
                mrps   = re.findall(r'"mrp"\s*:\s*(\d+)', raw)
                urls   = re.findall(r'"productUrl"\s*:\s*"(/[^"]+)"', raw)
                imgs   = re.findall(r'"src"\s*:\s*"(https://rukminim[^"]+)"', raw)

                for i in range(min(limit, len(names), len(prices))):
                    price = D(prices[i])
                    mrp   = D(mrps[i]) if i < len(mrps) and int(mrps[i]) > int(price) else None
                    href  = urls[i] if i < len(urls) else ""
                    results.append(ScrapedPrice(
                        retailer=retailer,
                        url=f"https://www.flipkart.com{href}" if href else "https://www.flipkart.com",
                        product_name=names[i],
                        current_price=price, mrp=mrp,
                        discount_pct=self.parse_discount(price, mrp),
                        in_stock=True,
                        image_url=imgs[i] if i < len(imgs) else None,
                        brand=names[i].split()[0] if names[i] else None,
                    ))
                return results
            except Exception as e:
                logger.debug(f"[Flipkart] embedded JSON parse failed: {e}")

        # Fallback: regex on raw HTML
        names  = re.findall(r'class="[^"]*s1Q9rs[^"]*">([^<]{5,120})<', html)
        prices = re.findall(r'class="[^"]*_30jeq3[^"]*"[^>]*>₹([0-9,]+)<', html)
        for i in range(min(limit, len(names), len(prices))):
            try:
                price = D(prices[i].replace(",", ""))
                results.append(ScrapedPrice(
                    retailer=retailer, url="https://www.flipkart.com",
                    product_name=names[i], current_price=price,
                    mrp=None, discount_pct=None, in_stock=True,
                ))
            except Exception:
                continue
        return results

    def _clean(self, r: ScrapedPrice) -> ScrapedPrice:
        """Apply validate_price + clean_name to any result."""
        r.current_price = self.validate_price(r.current_price, r.mrp)
        r.product_name  = self.clean_name(r.product_name or "")
        r.discount_pct  = self.parse_discount(r.current_price, r.mrp)
        return r

    # ─────────────────────────────────────────────────────────────────────────
    # IMAGE SEARCH — Google Lens → name → search_by_name (auto-discovery included)
    # ─────────────────────────────────────────────────────────────────────────
    async def search_by_image(self, image_bytes: bytes, mime: str = "image/jpeg") -> list[ScrapedPrice]:
        """
        Image → Google Lens → product name → search_by_name()
        search_by_name() already runs BOTH Engine 1 (profiles) + Engine 2 (auto-discovery).
        So image search gets full cross-retailer comparison automatically.
        """
        logger.info("[Universal] Image search: Google Lens → product name → full comparison")
        product_name = await self._google_lens_name(image_bytes, mime)
        if not product_name:
            logger.warning("[Universal] Lens returned no product name — cannot compare")
            return []
        
        logger.info(f"[Universal] Lens identified: '{product_name}' → running full comparison")
        # search_by_name has both Engine 1 (profiles) + Engine 2 (auto-discovery)
        result = await self.search_by_name(product_name)
        return result.get("results", []) if isinstance(result, dict) else result

    # ─────────────────────────────────────────────────────────────────────────
    # URL COMPARISON — scrape URL + auto-discover all other retailers
    # ─────────────────────────────────────────────────────────────────────────
    async def compare_from_url(self, url: str) -> list[ScrapedPrice]:
        """
        User pastes a URL (e.g. Croma product page).
        Returns price from that site AND comparison from ALL other retailers.

        Flow:
          1. Scrape the URL → get product name + this retailer's price
          2. Use product name → search_by_name() → Engine1 + Auto-discovery
          3. Merge: original URL result + all discovered retailers
          4. Deduplicate by domain (original site already scraped, don't double-show)

        Result: User pastes Croma URL → sees Croma + Amazon + Flipkart + Vijay Sales etc.
        """
        logger.info(f"[Universal] URL comparison: {url}")

        # Step 1: Scrape the pasted URL
        original = await self.scrape_url(url)
        if not original.product_name:
            logger.warning(f"[Universal] Could not extract product name from URL — only showing that site")
            return [original] if original.current_price else []

        product_name = original.product_name
        logger.info(f"[Universal] URL identified product: '{product_name}' → searching all retailers")

        # Step 2: Search all retailers with the extracted product name
        # search_by_name runs both profile-driven + auto-discovery in parallel
        other_results = await self.search_by_name(product_name)
        if isinstance(other_results, dict):
            other_results = other_results.get("results", [])

        # Step 3: Merge — put original site result first, then others
        original_domain = _domain(url)
        all_results = [original]
        for r in other_results:
            result_domain = _domain(r.url) if r.url else ""
            if result_domain and result_domain != original_domain:
                all_results.append(r)

        # Step 4: Deduplicate by domain
        all_results = self._deduplicate_by_domain(all_results)

        logger.info(
            f"[Universal] compare_from_url '{product_name}' → "
            f"{len(all_results)} retailers (original + {len(all_results)-1} discovered)"
        )
        return all_results

    async def search_product(self, query: str, limit: int = 5) -> list[ScrapedPrice]:
        results = await self.search_by_name(query)
        items = results.get("results", []) if isinstance(results, dict) else results
        return items[:limit]

<<<<<<< HEAD
    async def search_products(self, query: str, retailer: str = None, limit: int = 5) -> list[ScrapedPrice]:
        """Alias for search_product to match search service expectations"""
        return await self.search_product(query, limit)

=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    # ─────────────────────────────────────────────────────────────────────────
    # GOOGLE LENS
    # ─────────────────────────────────────────────────────────────────────────
    async def _google_lens_name(self, image_bytes: bytes, mime: str) -> Optional[str]:
        suffix = ".jpg" if "jpeg" in mime else ".png"
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            tmp.write(image_bytes)
            tmp.flush()
            tmp.close()
            return await self._lens_scrape(tmp.name)
        except Exception as e:
            logger.error(f"[Lens] Error: {e}")
            return None
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

    async def _lens_scrape(self, image_path: str) -> Optional[str]:
        ctx  = await self._new_context()
        page = await ctx.new_page()
        try:
            await page.goto("https://images.google.com", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(1500)

            cam = (await page.query_selector("[aria-label='Search by image']") or
                   await page.query_selector(".Gdd5U") or
                   await page.query_selector("[data-base-lens-url]"))
            if cam:
                await cam.click()
            else:
                await page.goto("https://lens.google.com/upload", wait_until="domcontentloaded", timeout=15000)

            await page.wait_for_timeout(1000)
            file_input = await page.query_selector("input[type='file']")
            if not file_input:
                upload_btn = (await page.query_selector("[aria-label='Upload a file']") or
                              await page.query_selector(".XjfJ5") or
                              await page.query_selector("a[href*='upload']"))
                if upload_btn:
                    await upload_btn.click()
                    await page.wait_for_timeout(800)
                    file_input = await page.query_selector("input[type='file']")

            if not file_input:
                await page.goto("https://lens.google.com/upload", wait_until="networkidle", timeout=15000)
                await page.wait_for_timeout(1000)
                file_input = await page.query_selector("input[type='file']")

            if not file_input:
                return None

            await file_input.set_input_files(image_path)
            await page.wait_for_timeout(4000)

            title_sels = [
                "h3", "[data-attrid='title'] span", ".uLMkR", ".iCkKE",
                "[role='heading']", ".Q9r3Y", ".sh-ds__trunc-txt",
            ]
            for sel in title_sels:
                el = await page.query_selector(sel)
                if el:
                    text = (await el.inner_text()).strip()
                    if text and len(text) > 4 and not text.lower().startswith("all result"):
                        return text

            title = await page.title()
            if title:
                cleaned = re.sub(r"[-–|].*Google.*", "", title, flags=re.IGNORECASE).strip()
                if cleaned and len(cleaned) > 4:
                    return cleaned
            return None
        except Exception as e:
            logger.error(f"[Lens] scrape error: {e}")
            return None
        finally:
            await ctx.close()

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _name_from_url(url: str) -> str:
        path = urlparse(url).path.rstrip("/")
        slug = path.split("/")[-1]
        slug = re.sub(r'\.\w{2,5}$', '', slug)
        slug = re.sub(r'[-_]\d{4,}$', '', slug)
        return slug.replace("-", " ").replace("_", " ").title() or url

    @staticmethod
    async def _pw_text(page, selector: str) -> Optional[str]:
        try:
            el = await page.query_selector(selector)
            return (await el.inner_text()).strip() if el else None
        except Exception:
            return None

    @staticmethod
    async def _pw_attr(page, selector: str, attr: str) -> Optional[str]:
        try:
            el = await page.query_selector(selector)
            return await el.get_attribute(attr) if el else None
        except Exception:
            return None

    @staticmethod
    async def _pw_meta(page, prop: str) -> Optional[str]:
        try:
            el = (await page.query_selector(f'meta[property="{prop}"]') or
                  await page.query_selector(f'meta[name="{prop}"]'))
            return await el.get_attribute("content") if el else None
        except Exception:
            return None


# ── Singleton ─────────────────────────────────────────────────────────────────
universal_scraper = UniversalScraper()
