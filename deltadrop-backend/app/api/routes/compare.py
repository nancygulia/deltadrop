"""
Product Comparison API — /api/v1/compare/*

Public endpoints for cross-platform price comparison.
Uses the optimized product_engine for scraping and comparison.

All responses follow a consistent format:
  {
    "query": "...",
    "best_price": float | null,
    "best_store_url": str | null,
    "stores": [...],
    "total_stores": int,
    "cached": bool
  }
"""
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.rate_limit import rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compare", tags=["Product Comparison"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=200)


class ScrapeURLRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=2000)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/search")
async def compare_search(body: CompareRequest, request: Request):
    """
    Cross-platform price comparison from text query.

    Search strategy (sequential — NOT parallel):
      1. Google organic scraper (primary — free)
      2. SerpAPI Shopping (ONLY if Google returns 0)

    Controls:
      - Semaphore(5) limits concurrent scrapes
      - 8s timeout per URL scrape
      - Price validation: ₹100 – ₹5,00,000
      - Results cached for 10 minutes

    Rate limit: 10 comparisons per minute per IP.
    """
    rate_limiter.check(request, "compare-search", max_requests=10, window_seconds=60)

    from app.scrapers.product_engine import compare_prices

    query = body.query.strip()
    if len(query) < 2:
        raise HTTPException(status_code=400, detail="Query too short")

    print("STEP 1: API HIT")
    try:
        result = await compare_prices(query)
    except Exception as e:
        import traceback
        print(f"API ERROR: {e}")
        traceback.print_exc()
        logger.error(f"[CompareAPI] ❌ Comparison failed for '{query}': {e}")
        raise HTTPException(
            status_code=500,
            detail="Comparison service temporarily unavailable. Try again.",
        )



    # Always return consistent format
    return {
        "query":          result.get("query", query),
        "best_price":     result.get("best_price"),
        "best_store_url": result.get("best_store_url"),
        "best_platform":  result.get("best_platform"),
        "stores":         result.get("stores", []),
        "total_stores":   result.get("total_stores", 0),
        "search_method":  result.get("search_method"),
        "cached":         result.get("cached", False),
        "error":          result.get("error"),
    }


@router.post("/url")
async def compare_url(body: ScrapeURLRequest, request: Request):
    """
    Scrape a single product URL from any supported platform.

    Returns structured product data:
      { title, price, availability, url, platform, mrp, ... }

    Controls:
      - Semaphore(5) for concurrency
      - 8s timeout
      - Price validation: ₹100 – ₹5,00,000

    Rate limit: 15 scrapes per minute per IP.
    """
    rate_limiter.check(request, "compare-url", max_requests=15, window_seconds=60)

    from app.scrapers.product_engine import get_product_data, detect_platform

    url = body.url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    platform = detect_platform(url)
    if not platform:
        logger.info(f"[CompareAPI] Scraping unknown platform: {url}")

    try:
        result = await get_product_data(url)
    except Exception as e:
        logger.error(f"[CompareAPI] ❌ Scrape failed for {url}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not scrape this URL. It may be temporarily unavailable.",
        )

    return result


@router.get("/platforms")
async def list_platforms():
    """
    List all supported e-commerce platforms for scraping.
    """
    from app.scrapers.product_engine import PLATFORM_MAP

    platforms = []
    for domain, name in PLATFORM_MAP.items():
        platforms.append({
            "domain": domain,
            "name": name,
            "search_url": f"https://www.{domain}",
        })

    return {
        "platforms": platforms,
        "total": len(platforms),
    }
