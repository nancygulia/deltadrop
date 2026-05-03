import logging
import asyncio
import time
import re
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import select, update, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.session import AsyncSessionLocal
# Import the full model registry BEFORE opening any DB session.
# This registers ALL SQLAlchemy mappers in the correct order, so that
# string-based relationships like relationship("User") can be resolved.
import app.models  # noqa: F401
from app.models.product import Product, RetailerListing, PriceHistory, RetailerName, PricePrediction
from app.scrapers.base import ScrapedPrice
from app.scrapers.universal import universal_scraper



logger = logging.getLogger(__name__)


def normalize_product_name(name: str, brand: str | None) -> str:
    n = (name or "").lower()
    n = re.sub(r'\(.*?\)', '', n)
    n = re.sub(r'\b(latest model|newest|premium|official|original|india|buy|online)\b', '', n)
    n = re.sub(r'[^a-z0-9\s]', ' ', n)
    n = " ".join(n.split())
    b = (brand or "").lower().strip()
    if b and b not in n:
        n = f"{b} {n}"
    return n


def normalize_search_query(query: str) -> str:
    """Normalize user queries so search behavior is case-insensitive."""
    return " ".join((query or "").strip().lower().split())

<<<<<<< HEAD

def _passes_price_sanity(query: str, result: ScrapedPrice) -> bool:
    """Reject obvious accessories/mismatches that pass text relevance for premium devices."""
    q = (query or "").lower()
    name = (result.product_name or "").lower()
    price = result.current_price

    if price is None:
        return True

    # ── Global price range validation (₹100 – ₹5,00,000) ─────────────────
    try:
        numeric_price = float(price)
    except (TypeError, ValueError):
        return True

    if numeric_price < 100 or numeric_price > 500_000:
        logger.info(f"[Filter] Rejected out-of-range price ₹{numeric_price}: {result.product_name}")
        return False

    device_query = any(token in q for token in [
        "iphone", "samsung galaxy", "oneplus", "pixel", "macbook", "ipad"
    ])
    if not device_query:
        return True

    accessory_terms = [
        "case", "cover", "tempered", "protector", "guard", "skin",
        "charger", "cable", "adapter", "earphone", "earbuds", "neckband",
        "headset", "holder", "stand",
    ]
    if any(term in name for term in accessory_terms):
        logger.info(f"[Filter] Rejected device accessory by title: {result.product_name}")
        return False

    if "iphone" in q and numeric_price < 25000:
        logger.info(
            f"[Filter] Rejected implausible iPhone price: {result.product_name} @ {numeric_price}"
        )
        return False
    if any(token in q for token in ["macbook", "ipad"]) and numeric_price < 15000:
        logger.info(
            f"[Filter] Rejected implausible Apple device price: {result.product_name} @ {numeric_price}"
        )
        return False

    return True


# ── In-Memory TTL Cache (10 minutes) ─────────────────────────────────────────

_SEARCH_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 600  # 10 minutes


def _cache_get(key: str) -> Any:
    """Return cached data if fresh (< 10 min), else None. (TEMPORARILY DISABLED)"""
    return None



def _cache_set(key: str, value: Any, ttl: int = _CACHE_TTL):
    """Store result in cache."""
    _SEARCH_CACHE[key] = (time.monotonic(), value)
    # Periodic GC
    if len(_SEARCH_CACHE) > 200:
        now = time.monotonic()
        stale = [k for k, (ts, _) in _SEARCH_CACHE.items() if now - ts > _CACHE_TTL]
        for k in stale:
            del _SEARCH_CACHE[k]
=======
def _cache_get(key: str):
    # Dummy cache for now, could be Redis
    return None

def _cache_set(key: str, value: Any, ttl: int = 300):
    pass
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3

class ScraperManager:
    """
    High-level interface used by both the scheduler and API endpoints. 
    Unified under the DID (Identity & Discovery) Engine.
    """

    async def search_and_track(self, query: str, retailers=None, category=None):
        """
        DeltaDrop DID (Identity & Discovery) Search.
        Unified entry point for accurate product search.
        """
        normalized_query = normalize_search_query(query)
        cache_key = f"did|{normalized_query}|{(category or '').lower()}"
        cached = _cache_get(cache_key)
        if cached:
            return cached

<<<<<<< HEAD
        results = await self.accurate_search(normalized_query, allowed_retailers=retailers)
=======
        results = await self.accurate_search(normalized_query)
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3

        # Determine diagnosis based on results
        diagnosis = None
        if not results:
            diagnosis = "no_matches"
        elif len(results) == 0:
            diagnosis = "all_filtered"
        elif all(getattr(r, "relevance_score", 0) < 0.5 for r in results):
            diagnosis = "low_confidence"
        elif any(getattr(r, "relevance_score", 0) < 0.3 for r in results):
            diagnosis = "mixed_confidence"

        # Persist anything with a non-zero relevance score (threshold increased to 0.5 for accuracy)
        high_relevance = [r for r in results if getattr(r, "relevance_score", 0) >= 0.5]
        if not high_relevance and results:
            # If nothing passes threshold, persist at least the top result so
            # the Track button works immediately after the first search.
            high_relevance = results[:1]
            # Mark as low confidence
            for r in high_relevance:
                r.low_confidence = True

        if high_relevance:
            logger.info(f"[Manager] Persisting {len(high_relevance)} matches for '{normalized_query}'...")
            await self._persist_results(high_relevance)

<<<<<<< HEAD
        # After persisting, look up real DB product IDs by slug so the frontend
        # can load real price history instead of generating demo/mock data.
        from app.utils.slugify import slugify
        slug_to_db_id: dict = {}
        try:
            async with AsyncSessionLocal() as _db:
                slugs = list({
                    slugify(normalize_product_name(r.product_name, getattr(r, "brand", None)))
                    for r in results
                })
                _res = await _db.execute(
                    select(Product.id, Product.slug).where(Product.slug.in_(slugs))
                )
                for row in _res.all():
                    slug_to_db_id[row.slug] = row.id
        except Exception as _e:
            logger.warning(f"[Manager] Could not fetch DB IDs after persist: {_e}")

        # Ensure results always contain at least partial data with confidence indicators
        enhanced_results = []
        for r in results:
            r_slug = slugify(normalize_product_name(r.product_name, getattr(r, "brand", None)))
            db_id = slug_to_db_id.get(r_slug)  # real integer ID or None
            result_dict = {
                "id": db_id,                   # ← real DB ID enables real price history chart
=======
        # Ensure results always contain at least partial data with confidence indicators
        enhanced_results = []
        for r in results:
            result_dict = {
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
                "product_name": r.product_name,
                "url": r.url,
                "retailer": r.retailer,
                "current_price": r.current_price,
                "image_url": getattr(r, "image_url", None),
                "relevance_score": getattr(r, "relevance_score", 0),
                "low_confidence": getattr(r, "low_confidence", False),
                "mrp": getattr(r, "mrp", None),
                "brand": getattr(r, "brand", None),
            }
            enhanced_results.append(result_dict)

        # Add diagnosis to the response
        response = {
            "results": enhanced_results,
            "diagnosis": diagnosis,
            "query": normalized_query,
            "total_found": len(results),
            "high_confidence_count": len(high_relevance)
        }

        _cache_set(cache_key, response)
        return response

    async def refresh_product(self, product_id: int):
        """
        Force-refresh all retailers for a specific product ID.
        Triggered manually or when data is detected as stale.
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Product).where(Product.id == product_id))
            product = result.scalar_one_or_none()
            if not product:
                logger.error(f"[Manager] Cannot refresh product {product_id}: not found")
                return

            logger.info(f"[Manager] Refreshing product: {product.name} (ID: {product_id})")
            # We use search_and_track which will call _persist_results
            # _persist_results will update existing listings and prune old ones
            await self.search_and_track(product.name)

<<<<<<< HEAD
    async def accurate_search(self, query: str, allowed_retailers: Optional[List[str]] = None):
        """
        Optimized search pipeline:
          1. Google organic scraper (primary — free, no API key)
          2. Universal scraper (profile-based, runs alongside Google)
          3. SerpAPI (ONLY if Google + Universal return nothing — costs money)

        Concurrency controls:
          - asyncio.Semaphore(5) for Google organic scrape tasks
          - 8s timeout per individual scrape
          - 10s timeout per search engine
        """
        from app.scrapers.serpapi import serpapi_scraper
        from app.scrapers.brand_retailer_map import get_allowed_retailers, detect_brand_from_query
        from app.scrapers.search_optimizer import search_optimizer
        import asyncio

        _scrape_sem = asyncio.Semaphore(5)  # Max 5 concurrent scrapes
=======
    async def accurate_search(self, query: str):
        """
        1. Try SerpAPI (Real API) with India-market search query.
        2. If fails/empty -> Fallback to UniversalScraper.
        3. Attach relevance scores for persistence filter.
        """
        from app.scrapers.serpapi import serpapi_scraper
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3

        query = normalize_search_query(query)
        logger.info(f"[Manager] Starting Accurate Search for: '{query}'")

<<<<<<< HEAD
        # Brand filter
        if not allowed_retailers:
            allowed_retailers = get_allowed_retailers(query)
        logger.info(f"[Manager] Allowed retailers: {allowed_retailers}")

        # ── Phase 1: Google Organic (primary) + Universal (parallel) ──────
        google_organic_results = []
        fallback_results = []

        async def run_google_organic():
            """Google organic search → discover URLs → scrape with semaphore."""
            try:
                from app.scrapers.google_organic import google_organic_scraper
                links = await asyncio.wait_for(
                    google_organic_scraper.search_product_links(query, max_links=6),
                    timeout=10.0,
                )
                if not links:
                    return []

                # Scrape discovered URLs with concurrency limit
                async def _sem_scrape(url: str):
                    try:
                        async with _scrape_sem:
                            return await asyncio.wait_for(
                                universal_scraper.scrape_url(url), timeout=8.0
                            )
                    except asyncio.TimeoutError:
                        logger.warning(f"[Manager] ⏱ Scrape timeout: {url}")
                        return None
                    except Exception as e:
                        logger.error(f"[Manager] ❌ Scrape failed: {url} — {e}")
                        return None

                tasks = [_sem_scrape(link["url"]) for link in links[:6]]
                raw = await asyncio.gather(*tasks)
                results = [r for r in raw if isinstance(r, ScrapedPrice) and (r.current_price or r.product_name)]
                logger.info(f"[Manager] Google Organic: {len(results)} results from {len(links)} links")
                return results
            except asyncio.TimeoutError:
                logger.warning("[Manager] ⏱ Google Organic search timed out")
                return []
            except Exception as e:
                logger.error(f"[Manager] ❌ Google Organic error: {e}")
                return []

        async def run_universal():
            try:
                engine_res = await asyncio.wait_for(
                    universal_scraper.search_by_name(query, allowed_retailers=allowed_retailers),
                    timeout=10.0,
                )
                return engine_res.get("results") or []
            except asyncio.TimeoutError:
                logger.warning("[Manager] ⏱ Universal Scraper timed out")
                return []
            except Exception as e:
                logger.error(f"[Manager] ❌ Universal Scraper error: {e}")
                return []

        # Run Google + Universal in parallel (both are free/local)
        gathered = await asyncio.gather(run_google_organic(), run_universal())
        google_organic_results = gathered[0]
        fallback_results = gathered[1]

        # ── Phase 2: SerpAPI ONLY if Phase 1 returned nothing ─────────────
        api_results = []
        has_phase1_results = bool(google_organic_results) or bool(fallback_results)

        if not has_phase1_results:
            logger.info("[Manager] Phase 1 returned 0 results — running SerpAPI fallback")
            try:
                enriched_query = query
                enriched_query = f"{query} buy online india price"
                api_results = await asyncio.wait_for(
                    serpapi_scraper.search_shopping(enriched_query), timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning("[Manager] ⏱ SerpAPI timed out")
                api_results = []
            except Exception as e:
                logger.error(f"[Manager] ❌ SerpAPI error: {e}")
                api_results = []
        else:
            logger.info(
                f"[Manager] Phase 1 sufficient: {len(google_organic_results)} Google + "
                f"{len(fallback_results)} Universal — skipping SerpAPI"
            )

        # ── Score & filter SerpAPI results ────────────────────────────────
        valid_api = []
        for r in api_results:
            score = universal_scraper.calculate_relevance(query, r.product_name, retailer=r.retailer, url=r.url)
            r.relevance_score = score
            if score < 0.3:
                logger.debug(f"[Manager] Skipped low relevance: {r.product_name} ({score:.2f})")
                continue
            if not _passes_price_sanity(query, r):
=======
        # Enrich query for better Indian retail coverage
        enriched_query = query
        if not any(kw in query.lower() for kw in ["buy", "india", "price", "online"]):
            enriched_query = f"{query} price India"

        api_results = await serpapi_scraper.search_shopping(enriched_query)

        valid_api = []
        for r in api_results:
            # 1. Calculate relevance
            score = universal_scraper.calculate_relevance(query, r.product_name, retailer=r.retailer, url=r.url)
            r.relevance_score = score
            
            # 2. Filter by threshold (0.5 for search results)
            if score < 0.5:
                logger.debug(f"[Manager] Skipping low relevance result: {r.product_name} ({score:.2f})")
                continue

            # 3. Direct Product Page Validation
            is_direct = self._is_direct_product_url(r.url)
            if not is_direct:
                logger.debug(f"[Manager] Skipping non-direct URL: {r.url}")
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
                continue
            valid_api.append(r)

        if valid_api:
<<<<<<< HEAD
            logger.info(f"[Manager] SerpAPI: {len(valid_api)} valid results for '{query}'")

        # ── Score & filter Universal results ──────────────────────────────
        valid_fallback = []
        for r in fallback_results:
            retailer_matches = any(
                search_optimizer._source_matches_retailer(allowed, r.retailer)
                for allowed in allowed_retailers
            )
            if not retailer_matches:
                logger.debug(f"[Manager] Skipped blocked retailer: {r.product_name} ({r.retailer})")
                continue

=======
            logger.info(f"[Manager] SerpAPI returned {len(valid_api)} results for '{query}'.")
            return valid_api

        logger.warning(f"[Manager] SerpAPI empty. Falling back to universal scraping for '{query}'.")
        engine_res = await universal_scraper.search_by_name(query)
        fallback_results = engine_res.get("results") or []

        for r in fallback_results:
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
            if not hasattr(r, "relevance_score"):
                r.relevance_score = universal_scraper.calculate_relevance(
                    query, r.product_name, retailer=r.retailer, url=r.url
                )
<<<<<<< HEAD
            if r.relevance_score >= 0.5 and _passes_price_sanity(query, r):
                valid_fallback.append(r)

        logger.info(f"[Manager] Universal: {len(valid_fallback)} valid results for '{query}'")

        # ── Score & filter Google Organic results ─────────────────────────
        valid_organic = []
        for r in google_organic_results:
            score = universal_scraper.calculate_relevance(query, r.product_name, retailer=r.retailer, url=r.url)
            r.relevance_score = score
            if score >= 0.3 and _passes_price_sanity(query, r):
                valid_organic.append(r)

        if valid_organic:
            logger.info(f"[Manager] Google Organic: {len(valid_organic)} valid results for '{query}'")

        # ── Merge + deduplicate ───────────────────────────────────────────
        # Priority: Google Organic (free live) > Universal (profile) > SerpAPI (paid)
        combined = []
        seen = set()
        for r in valid_organic + valid_fallback + valid_api:
            key = (r.url or "").strip().lower() or f"{r.retailer}:{r.product_name}:{r.current_price}"
            if key in seen:
                continue
            seen.add(key)
            combined.append(r)

        logger.info(f"[Manager] ✅ Combined: {len(combined)} unique results for '{query}'")
        return combined
=======

        return fallback_results
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3

    async def _persist_results(self, results):
        """
        Persist ScrapedPrice objects to the DB.
        Each record is wrapped in a savepoint so one failure cannot roll back others.
        """
        from app.utils.slugify import slugify
        # Track updated product IDs to prune old retailers later
        updated_product_ids = set()
        active_retailers_per_product = {} # product_id -> set of retailer enums

        async with AsyncSessionLocal() as db:
            for r in results:
                # Per-record savepoint prevents one bad row from aborting the whole batch
                savepoint = await db.begin_nested()
                try:
                    # 1. Find or create Product
                    norm_name = normalize_product_name(r.product_name, getattr(r, 'brand', None))
                    slug = slugify(norm_name)
                    res = await db.execute(select(Product).where(Product.slug == slug))
                    product = res.scalar_one_or_none()

                    if not product:
                        product = Product(
                            name=r.product_name,
                            slug=slug,
                            brand=r.brand or r.product_name.split()[0],
                            category=self._infer_category(r.product_name, r.retailer),
                            image_url=r.image_url,
                        )
                        db.add(product)
                        try:
                            await db.flush()
                        except IntegrityError:
                            await savepoint.rollback()
                            savepoint = await db.begin_nested()
                            res = await db.execute(select(Product).where(Product.slug == slug))
                            product = res.scalar_one_or_none()
                            if not product:
                                raise

                    r.product_id = product.id
                    updated_product_ids.add(product.id)

                    retailer_enum = None
                    target_retailer = r.retailer.lower().strip()
                    for e in RetailerName:
                        if e.value.lower().strip() in target_retailer or target_retailer in e.value.lower().strip() or target_retailer.replace('.in', '') == e.value.lower().strip().replace('.in', ''):
                            retailer_enum = e
                            break
                    if not retailer_enum:
                        retailer_enum = RetailerName.amazon
                    
                    res = await db.execute(
                        select(RetailerListing).where(
                            RetailerListing.product_id == product.id,
                            RetailerListing.retailer   == retailer_enum,
                        )
                    )
                    listing = res.scalar_one_or_none()

                    # Allow None for in_stock if unknown
                    safe_stock = r.in_stock
                    safe_mrp   = r.mrp  # mrp is intentionally Optional; DB column allows NULL

                    if not listing:
                        listing = RetailerListing(
                            product_id    = product.id,
                            retailer      = retailer_enum,
                            retailer_url  = r.url,
                            current_price = r.current_price,
                            mrp           = safe_mrp,
                            in_stock      = safe_stock,
                            last_scraped_at = datetime.now(timezone.utc),
                        )
                        db.add(listing)
                        await db.flush()
                    else:
                        listing.current_price   = r.current_price
                        listing.mrp             = safe_mrp
                        listing.in_stock        = safe_stock
                        listing.retailer_url    = r.url
                        listing.last_scraped_at = datetime.now(timezone.utc)
                        listing.is_active       = True

                    r.listing_id = listing.id
                    if product.id not in active_retailers_per_product:
                        active_retailers_per_product[product.id] = set()
                    active_retailers_per_product[product.id].add(retailer_enum)

                    # 3. Append PriceHistory (always insert on every scrape)
                    dpct = r.discount_pct
                    if dpct is None and r.current_price and safe_mrp and safe_mrp > 0:
                        dpct = ((safe_mrp - r.current_price) / safe_mrp) * 100

<<<<<<< HEAD
                    self._append_price_history(
                        db,
                        product_id=product.id,
                        listing_id=listing.id,
                        retailer=retailer_enum,
                        price=r.current_price,
                        mrp=safe_mrp,
                        discount_pct=dpct,
                        in_stock=safe_stock,
                    )
=======
                    db.add(PriceHistory(
                        product_id  = product.id,
                        listing_id  = listing.id,
                        retailer    = retailer_enum,
                        price       = r.current_price,
                        mrp         = safe_mrp,
                        discount_pct= dpct,
                        in_stock    = safe_stock,
                    ))
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3

                    await savepoint.commit()
                    logger.debug(f"[Manager] Persisted: {r.product_name} @ {r.retailer}")

                except Exception as e:
                    await savepoint.rollback()
                    logger.error(f"[Manager] Savepoint rollback for '{r.product_name}': {e}")
                    continue

            # 4. Prune old retailers
            for pid in updated_product_ids:
                found_retailers = active_retailers_per_product.get(pid, set())
                await db.execute(
                    update(RetailerListing)
                    .where(
                        RetailerListing.product_id == pid,
                        RetailerListing.retailer.notin_(found_retailers)
                    )
                    .values(is_active=False)
                )

            await db.commit()

    async def scrape_listing(self, listing: RetailerListing) -> Optional[ScrapedPrice]:
        """Scrape one specific RetailerListing by its URL and update the DB."""
        try:
            result = await universal_scraper.scrape_url(listing.retailer_url)
            if result.is_valid:
                await self._save_price_point(listing, result)
            else:
                await self._record_error(listing, result.error or "Unknown error")
            return result
        except Exception as e:
            logger.error(f"[Manager] Error scraping listing {listing.id}: {e}")
            await self._record_error(listing, str(e))
            return None

    async def refresh_alerted_products_via_serpapi(self):
        """
        Called by APScheduler (separate from alert checks).
        Only updates products that have active price alerts via SerpAPI.
        Highly optimized to conserve API credits.
        """
        from app.models.product import PriceAlert, Product
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Product.name).distinct()
                .join(PriceAlert, PriceAlert.product_id == Product.id)
                .where(PriceAlert.is_active == True)
            )
            product_names = result.scalars().all()

        if not product_names:
            logger.info("[Manager] Scheduled SerpAPI Update: 0 active alerts, skipping.")
            return {"success": 0, "errors": 0, "total": 0}

        logger.info(f"[Manager] Scheduled SerpAPI Update: refreshing {len(product_names)} alerted products.")

        success = 0
        errors = 0
        # We process sequentially to avoid getting instantly rate-limited by SerpAPI free tier
        for name in product_names:
            try:
                # search_and_track does SerpAPI fetch + full persistence
                await self.search_and_track(name)
                success += 1
            except Exception as e:
                logger.error(f"[Manager] SerpAPI refresh failed for '{name}': {e}")
                errors += 1

        logger.info(f"[Manager] SerpAPI Update complete: {success} success, {errors} errors")
        return {"success": success, "errors": errors, "total": len(product_names)}

    async def add_product_from_url(self, url: str, retailer_name: str, db: Any) -> Optional[Product]:
        """
        Given a product URL, scrape it, create/find Product + RetailerListing.
        """
        scraped = await universal_scraper.scrape_url(url)
        if not scraped.is_valid:
            logger.warning(f"[Manager] Invalid scrape result for {url}: {scraped.error}")
            return None

        from app.utils.slugify import slugify
        slug = slugify(normalize_product_name(scraped.product_name, scraped.brand))

        result  = await db.execute(select(Product).where(Product.slug == slug))
        product = result.scalar_one_or_none()

        if not product:
            product = Product(
                name     = scraped.product_name,
                slug     = slug,
                brand    = scraped.brand,
                category = self._infer_category(scraped.product_name, retailer_name),
                image_url= scraped.image_url,
                specs    = str(scraped.specs),
            )
            db.add(product)
            await db.flush()

        # Resolve retailer enum safely
        try:
            retailer_enum = RetailerName(retailer_name)
        except ValueError:
            retailer_enum = RetailerName.amazon

        result  = await db.execute(
            select(RetailerListing).where(
                RetailerListing.product_id == product.id,
                RetailerListing.retailer   == retailer_enum,
            )
        )
        listing = result.scalar_one_or_none()

        # Use safe_in_stock to avoid NOT NULL violation
        safe_stock = scraped.safe_in_stock

        if not listing:
            listing = RetailerListing(
                product_id    = product.id,
                retailer      = retailer_enum,
                retailer_url  = url,
                current_price = scraped.current_price,
                mrp           = scraped.mrp,
                in_stock      = safe_stock,
                last_scraped_at = datetime.now(timezone.utc),
            )
            db.add(listing)
            await db.flush()
        else:
            listing.current_price    = scraped.current_price
            listing.mrp              = scraped.mrp
            listing.in_stock         = safe_stock
            listing.last_scraped_at  = datetime.now(timezone.utc)
            listing.scrape_errors    = 0

        # Compute discount_pct if missing
        dpct = scraped.discount_pct
        if dpct is None and scraped.current_price and scraped.mrp and scraped.mrp > 0:
            dpct = ((scraped.mrp - scraped.current_price) / scraped.mrp) * 100

<<<<<<< HEAD
        self._append_price_history(
            db,
            product_id=product.id,
            listing_id=listing.id,
            retailer=retailer_enum,
            price=scraped.current_price,
            mrp=scraped.mrp,
            discount_pct=dpct,
            in_stock=safe_stock,
        )
=======
        db.add(PriceHistory(
            product_id   = product.id,
            listing_id   = listing.id,
            retailer     = retailer_enum,
            price        = scraped.current_price,
            mrp          = scraped.mrp,
            discount_pct = dpct,
            in_stock     = safe_stock,
        ))
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
        await db.commit()
        await db.refresh(product)

        logger.info(f"[Manager] Tracked: {product.name} @ ₹{scraped.current_price} on {retailer_name}")
        return product

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _save_price_point(self, listing: RetailerListing, result: ScrapedPrice):
        async with AsyncSessionLocal() as db:
            safe_stock = result.safe_in_stock
            dpct = result.discount_pct
            if dpct is None and result.current_price and result.mrp and result.mrp > 0:
                dpct = ((result.mrp - result.current_price) / result.mrp) * 100

            await db.execute(
                update(RetailerListing)
                .where(RetailerListing.id == listing.id)
                .values(
                    current_price   = result.current_price,
                    mrp             = result.mrp,
                    in_stock        = safe_stock,
                    last_scraped_at = datetime.now(timezone.utc),
                    scrape_errors   = 0,
                )
            )
<<<<<<< HEAD
            self._append_price_history(
                db,
                product_id=listing.product_id,
                listing_id=listing.id,
                retailer=listing.retailer,
                price=result.current_price,
                mrp=result.mrp,
                discount_pct=dpct,
                in_stock=safe_stock,
            )
            await db.commit()

    @staticmethod
    def _append_price_history(
        db,
        *,
        product_id: int,
        listing_id: int,
        retailer,
        price,
        mrp,
        discount_pct,
        in_stock,
    ):
        # Keep every listing update mirrored into price history so charts and
        # prediction jobs always have a fresh event stream to consume.
        db.add(PriceHistory(
            product_id   = product_id,
            listing_id   = listing_id,
            retailer     = retailer,
            price        = price,
            mrp          = mrp,
            discount_pct = discount_pct,
            in_stock     = in_stock,
            recorded_at  = datetime.now(timezone.utc),
        ))

=======
            db.add(PriceHistory(
                product_id   = listing.product_id,
                listing_id   = listing.id,
                retailer     = listing.retailer,
                price        = result.current_price,
                mrp          = result.mrp,
                discount_pct = dpct,
                in_stock     = safe_stock,
            ))
            await db.commit()

>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    async def _record_error(self, listing: RetailerListing, error: str):
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(RetailerListing)
                .where(RetailerListing.id == listing.id)
                .values(scrape_errors=RetailerListing.scrape_errors + 1)
            )
            await db.commit()

    @staticmethod
    def _infer_category(name: str, retailer: str) -> str:
        name_lower = name.lower()
        if retailer in ("Myntra", "AJIO"):
            return "Fashion"
        if retailer == "Nykaa":
            return "Accessories"
        if any(k in name_lower for k in ["iphone","samsung galaxy","pixel","oneplus","redmi","realme","poco"]):
            return "Smartphones"
        if any(k in name_lower for k in ["macbook","laptop","notebook","thinkpad","xps","rog","legion"]):
            return "Laptops"
        if any(k in name_lower for k in ["airpod","headphone","earphone","earbuds","wh-","qc"]):
            return "Headphones"
        if any(k in name_lower for k in ["camera","mirrorless","dslr","gopro"]):
            return "Cameras"
        if any(k in name_lower for k in ["tv","television","oled","qled"]):
            return "Television"
        if any(k in name_lower for k in ["monitor","display","screen"]):
            return "Monitors"
        if any(k in name_lower for k in ["playstation","xbox","nintendo","gaming"]):
            return "Gaming"
        if any(k in name_lower for k in ["fridge","washer","ac ","air conditioner","microwave"]):
            return "Appliances"
        if any(k in name_lower for k in ["shoe","sneaker","boot","sandal"]):
            return "Shoes"
        if any(k in name_lower for k in ["watch","smartwatch"]):
            return "Smartwatches"
        if any(k in name_lower for k in ["ipad","tablet","tab "]):
            return "Tablets"
        return "Accessories"

    def _is_direct_product_url(self, url: str) -> bool:
        """
        Heuristic to check if a URL is likely a direct product page.
        Filters out search results, category pages, and generic homepages.
        """
        if not url: return False
        u = url.lower()
        # Google Shopping redirects are often intermediate but we allow them if we can't find direct
        if "google.com/shopping/product/" in u or "google.com/url?" in u:
            return True
            
        # Common patterns for non-product pages
        blacklist = [
            "/search", "/category", "/browse", "/collections", 
            "?q=", "&q=", "query=", "filter=", "sort_by="
        ]
        if any(b in u for b in blacklist):
            # Check if it also has product indicators like /p/ or /dp/ or /product/
            product_indicators = ["/p/", "/dp/", "/product/", "/gp/", "/itm/", "/ip/"]
            if not any(i in u for i in product_indicators):
                return False
                
        return True

# Singleton instance
scraper_manager = ScraperManager()
