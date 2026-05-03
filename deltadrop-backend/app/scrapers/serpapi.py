import logging
import re
import hashlib
import aiohttp
import requests
from typing import List
from decimal import Decimal
from urllib.parse import unquote
from app.core.config import settings
from app.scrapers.base import ScrapedPrice

logger = logging.getLogger(__name__)


def _parse_price(raw) -> Decimal | None:
    """Parse any Indian price string into a Decimal. Returns None on failure."""
    if not raw:
        return None
    cleaned = (
        str(raw)
        .replace(",", "")
        .replace("₹", "")
        .replace("Rs", "")
        .replace("INR", "")
        .strip()
    )
    # strip leading/trailing non-digit chars that remain
    cleaned = re.sub(r"[^\d.]", "", cleaned)
    try:
        val = Decimal(cleaned)
        return val if val > 0 else None
    except Exception:
        return None


def _resolve_link(item: dict) -> str:
    """
    Return the most direct retailer URL available.
    Priority: direct_link → link (unwrapped if Google redirect) → product_link
    Google Shopping product pages are allowed as a last-resort fallback.
    """
    # 1. SerpAPI's direct_link field (cleanest option)
    direct = item.get("direct_link") or ""
    if direct and not direct.startswith("https://www.google"):
        return direct

    # 2. main link field — unwrap Google redirect if needed
    link = item.get("link") or ""
    if link and "google.com/url?" in link:
        match = re.search(r"[?&]url=([^&]+)", link)
        if match:
            link = unquote(match.group(1))
    if link and "google.com/search" not in link:
        return link

    product_link = item.get("product_link") or ""
    if product_link:
        return product_link

    # 3. Fallback: empty string (handled upstream)
    return ""


def _extract_mrp(extensions: list, price: Decimal) -> Decimal | None:
    """
    Try to extract MRP from extension strings.
    1. Look for explicit 'list price', 'mrp', 'original price' labels.
    2. Back-calculate from discount percentage.
    3. Fallback: return current_price (i.e. no discount, but never None).
    """
    for ext in extensions:
        ext_lower = ext.lower()
        if any(kw in ext_lower for kw in ["list price", "mrp", "original price", "was"]):
            mrp_match = re.search(r"[\d,]+", ext)
            if mrp_match:
                candidate = _parse_price(mrp_match.group(0))
                if candidate and candidate >= price:
                    return candidate

    # Back-calculate from discount percentage
    for ext in extensions:
        if "%" in ext and "off" in ext.lower():
            pct_match = re.search(r"(\d+)%", ext)
            if pct_match:
                pct = Decimal(pct_match.group(1))
                if 1 <= pct < 90:
                    try:
                        calculated = (price / (1 - pct / 100)).quantize(Decimal("1"))
                        if calculated > price:
                            return calculated
                    except Exception:
                        pass

    # Fallback: Unknown MRP
    return None


def _parse_stock_status(item: dict) -> bool:
    """
    Availability detection. Returns bool or None.
    Defaults to None (assume unknown) when data is ambiguous.
    """
    extensions = " ".join(str(e) for e in item.get("extensions", []))
    availability = str(item.get("availability", ""))
    delivery = str(item.get("delivery", ""))

    combined_text = f"{extensions} {availability} {delivery}".lower()

    # Explicit out-of-stock signals
    if any(kw in combined_text for kw in ["out of stock", "unavailable", "sold out", "currently unavailable"]):
        return False

    # Explicit in-stock signals
    if any(kw in combined_text for kw in ["in stock", "available", "delivery", "ships", "buy"]):
        return True

    # Check link for cart/buy signal
    link = str(item.get("link", "")).lower()
    if "buy" in link or "cart" in link or "checkout" in link:
        return True

    # Ambiguous/missing data → return None (unknown stock)
    return None


def _parse_item(item: dict) -> ScrapedPrice | None:
    """
    Parse one SerpAPI shopping result item into a ScrapedPrice.
    Returns None if price is missing/unparseable.
    """
    price = _parse_price(item.get("price"))
    if price is None:
        return None

    retailer = item.get("source", "Unknown")
    link = _resolve_link(item)
    image = item.get("thumbnail")
    extensions = item.get("extensions", [])
    mrp = _extract_mrp(extensions, price)
    in_stock = _parse_stock_status(item)

    return ScrapedPrice(
        retailer      = retailer,
        url           = link,
        product_name  = item.get("title", ""),
        current_price = price,
        mrp           = mrp,
        discount_pct  = None,
        in_stock      = in_stock,
        image_url     = image,
    )


class SerpAPIScraper:
    """
    SerpAPI (Google Shopping) Scraper.
    Parses BOTH shopping_results and inline_shopping_results for maximum retailer coverage.
    """

    BASE_URL = "https://serpapi.com/search.json"

    def __init__(self):
        self.api_key = settings.SERPAPI_API_KEY

    async def search_candidates(self, query: str, limit: int = 12) -> list[dict]:
        """
        Lightweight search mode for product discovery (no DB persistence).
        """
        if not self.api_key or "placeholder" in self.api_key.lower() or "your_" in self.api_key.lower():
            logger.warning("[SerpAPI] No valid API key configured. Set SERPAPI_API_KEY in environment or .env file. Candidate search skipped.")
            logger.info("[SerpAPI] To get results: 1) Sign up at serpapi.com 2) Get API key 3) Set SERPAPI_API_KEY=your_key")
            return []

        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": self.api_key,
            "gl": "in",
            "hl": "en",
            "num": "20",  # Request more results
            "device": "desktop",  # Desktop results
            "safe": "active",  # Safe search
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params, timeout=15) as response:
                    response.raise_for_status()
                    data = await response.json()
            raw_items = (data.get("shopping_results", []) + data.get("inline_shopping_results", []))[: limit * 3]
            grouped: dict[str, dict] = {}
            for item in raw_items:
                title = (item.get("title") or "").strip()
                if not title:
                    continue
                key = title.lower()
                source = item.get("source", "Unknown")
                parsed_price = _parse_price(item.get("price"))
                approx = float(parsed_price) if parsed_price is not None else None
                if key not in grouped:
                    grouped[key] = {
                        "selection_id": hashlib.sha1(f"{title}|{source}".encode("utf-8")).hexdigest()[:20],
                        "name": title,
                        "image": item.get("thumbnail"),
                        "approximate_price": approx,
                        "price_range": {"min": approx, "max": approx} if approx is not None else None,
                        "retailer_sources": [source],
                    }
                else:
                    entry = grouped[key]
                    if source not in entry["retailer_sources"]:
                        entry["retailer_sources"].append(source)
                    if approx is not None:
                        if entry["price_range"] is None:
                            entry["price_range"] = {"min": approx, "max": approx}
                        else:
                            entry["price_range"]["min"] = min(entry["price_range"]["min"], approx)
                            entry["price_range"]["max"] = max(entry["price_range"]["max"], approx)
            return list(grouped.values())[:limit]
        except Exception as exc:
            logger.error("[SerpAPI] Candidate search failed: %s", exc)
            return []

    async def search_shopping(self, query: str, limit: int = 20) -> List[ScrapedPrice]:
        """
        Search Google Shopping via SerpAPI (gl=in for Indian market).
        Merges shopping_results + inline_shopping_results and deduplicates by retailer.
        """
        if not self.api_key or "placeholder" in self.api_key.lower() or "your_" in self.api_key.lower():
            logger.warning("[SerpAPI] No valid API key. Skipping.")
            return []

        params = {
            "engine":      "google_shopping",
            "q":           query,
            "api_key":     self.api_key,
            "gl":          "in",
            "hl":          "en",
            "direct_link": "true",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    response.raise_for_status()
                    data = await response.json()

            # ── Issue 1 Fix: Merge BOTH result sections ──────────────────────
            raw_items: list[dict] = []
            raw_items.extend(data.get("shopping_results", []))
            raw_items.extend(data.get("inline_shopping_results", []))

            logger.info(
                f"[SerpAPI] '{query}': {len(data.get('shopping_results', []))} shopping + "
                f"{len(data.get('inline_shopping_results', []))} inline = {len(raw_items)} total raw items"
            )

            # Parse all items
            parsed: list[ScrapedPrice] = []
            for item in raw_items[:limit]:
                try:
                    result = _parse_item(item)
                    if result:
                        parsed.append(result)
                except Exception as e:
                    logger.debug(f"[SerpAPI] Row parse error: {e}")
                    continue

            # ── Deduplicate: keep one entry per retailer (best price wins) ───
            seen_retailers: dict[str, ScrapedPrice] = {}
            for r in parsed:
                key = r.retailer.lower().strip()
                if key not in seen_retailers:
                    seen_retailers[key] = r
                else:
                    # Keep the cheaper one
                    existing = seen_retailers[key]
                    if r.current_price and existing.current_price and r.current_price < existing.current_price:
                        seen_retailers[key] = r

            results = list(seen_retailers.values())

            # Sort: Amazon and Flipkart first, then by price
            results.sort(key=lambda x: self._ranking_score(x), reverse=True)

            in_stock_count = sum(1 for r in results if r.in_stock)
            logger.info(
                f"[SerpAPI] '{query}': {len(results)} unique retailers "
                f"({in_stock_count} in stock)"
            )
            return results

        except Exception as e:
            logger.error(f"[SerpAPI] Search failed: {e}")
            return []

    def _ranking_score(self, item: ScrapedPrice) -> int:
        score = 0
        retailer_lower = item.retailer.lower()
        if "amazon" in retailer_lower:
            score += 100
        elif "flipkart" in retailer_lower:
            score += 90
        elif "myntra" in retailer_lower:
            score += 70
        elif "nykaa" in retailer_lower:
            score += 65
        elif "ajio" in retailer_lower:
            score += 60
        elif "croma" in retailer_lower:
            score += 55
        elif "reliance" in retailer_lower:
            score += 50
        # Also rank by price (cheaper = higher)
        if item.current_price:
            score -= int(item.current_price) // 1000
        return score


serpapi_scraper = SerpAPIScraper()
