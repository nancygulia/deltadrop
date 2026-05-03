<<<<<<< HEAD
from typing import Optional, Any
=======
from typing import Optional
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File, Request
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.product import (
    Product, RetailerListing, PriceHistory,
    PricePrediction, WatchlistItem, RetailerName,
)
from app.scrapers.manager import scraper_manager
from app.scrapers.manager import normalize_search_query
from app.scrapers.price_verifier import verify_retailer_prices
from app.ml.predictor import run_prediction_for_product
from app.core.config import settings

router = APIRouter(prefix="/products", tags=["Products"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class TrackURLRequest(BaseModel):
    url:         str
    retailer:    str   # "Amazon.in" | "Flipkart" | "Myntra" | ...

class SearchRequest(BaseModel):
    query:     str
    retailers: Optional[list[str]] = None
    category:  Optional[str]       = None

class CompareURLRequest(BaseModel):
    url: str   # Any product URL from any Indian retailer

class ProductSelectionRequest(BaseModel):
    selection_id: str
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None

<<<<<<< HEAD
class SelectionDrillDownRequest(BaseModel):
    selection_id: str
    query: str

=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3

# ── Helper ─────────────────────────────────────────────────────────────────────

def _product_dict(p: Product) -> dict:
    listings = [l for l in (p.retailer_listings or []) if l.is_active]

    # Best price: cheapest across in-stock listings; fall back to any active listing
    in_stock_prices = [l.current_price for l in listings if l.current_price and l.in_stock]
    any_prices      = [l.current_price for l in listings if l.current_price]
    best_price = min(in_stock_prices) if in_stock_prices else (min(any_prices) if any_prices else None)

    return {
        "id":               p.id,
        "name":             p.name,
        "slug":             p.slug,
        "brand":            p.brand,
        "category":         p.category.value,
        "description":      p.description,
        "image_url":        p.image_url,
        "best_price":       float(best_price) if best_price else None,
        "retailers_scanned": len(listings),
        "created_at":       p.created_at.isoformat(),
        "retailers": [
            {
                "retailer":      l.retailer.value,
                "url":           l.retailer_url,
<<<<<<< HEAD
                "retailer_url":  l.retailer_url,
                "buy_now_url":   l.retailer_url,
                "current_price": float(l.current_price) if l.current_price else None,
                "mrp":           float(l.mrp) if l.mrp else None,
                "in_stock":      l.safe_in_stock,
=======
                "current_price": float(l.current_price) if l.current_price else None,
                "mrp":           float(l.mrp) if l.mrp else None,
                "in_stock":      bool(l.safe_in_stock),
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
                "last_scraped":  l.last_scraped_at.isoformat() if l.last_scraped_at else None,
                "verified_at":   l.last_scraped_at.isoformat() if l.last_scraped_at else None,
                "verification_source": "scraperapi" if l.last_scraped_at else "cached",
            }
            for l in listings
        ],
    }


<<<<<<< HEAD
async def _seed_initial_price_history(db: AsyncSession, product: Product) -> bool:
    """
    Seed the first persisted price-history snapshot for products that do not
    yet have any rows. This keeps charts alive on the first successful lookup.
    """
    if not product or not product.id:
        return False

    existing = await db.execute(
        select(PriceHistory.id).where(PriceHistory.product_id == product.id).limit(1)
    )
    if existing.scalar_one_or_none():
        return False

    listings = [
        l for l in (product.retailer_listings or [])
        if l.is_active and l.current_price is not None
    ]
    if not listings:
        return False

    snapshot_time = datetime.now(timezone.utc)
    for listing in listings:
        current_price = float(listing.current_price)
        mrp = float(listing.mrp) if listing.mrp else None
        discount_pct = None
        if mrp and mrp > 0:
            discount_pct = ((mrp - current_price) / mrp) * 100

        db.add(PriceHistory(
            product_id   = product.id,
            listing_id   = listing.id,
            retailer     = listing.retailer,
            price        = listing.current_price,
            mrp          = listing.mrp,
            discount_pct = discount_pct,
            in_stock     = listing.safe_in_stock,
            recorded_at  = snapshot_time,
        ))

    await db.commit()
    return True


def _search_rows(payload: Any) -> list:
    if isinstance(payload, dict):
        rows = payload.get("results")
        return rows if isinstance(rows, list) else []
    if isinstance(payload, list):
        return payload
    return []


def _row_get(row: Any, key: str, default=None):
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _row_is_valid(row: Any) -> bool:
    if isinstance(row, dict):
        return row.get("current_price") is not None or row.get("price") is not None
    return bool(getattr(row, "is_valid", False))


=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("")
async def list_products(
    category: Optional[str]  = Query(None),
    search:   Optional[str]  = Query(None),
    page:     int            = Query(1,  ge=1),
    limit:    int            = Query(20, ge=1, le=100),
    sort:     str            = Query("created_at"),
    order:    str            = Query("desc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Product)
        .options(selectinload(Product.retailer_listings))
        .where(Product.is_active == True)
    )

    if category:
        query = query.where(Product.category == category)
    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))

    sort_col = getattr(Product, sort, Product.created_at)
    query    = query.order_by(desc(sort_col) if order == "desc" else sort_col)

    # Count
    count_q = select(func.count(Product.id)).where(Product.is_active == True)
    if category:
        count_q = count_q.where(Product.category == category)
    if search:
        count_q = count_q.where(Product.name.ilike(f"%{search}%"))

    total  = (await db.execute(count_q)).scalar()
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    prods  = result.scalars().all()

    return {
        "data":  [_product_dict(p) for p in prods],
        "total": total,
        "page":  page,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db)
):
    """Accurate Autocomplete Suggestion engine (Requirement 1 Extra)."""
    # Simply find names containing the query from existing products
    query = (
        select(Product.id, Product.name)
        .where(Product.name.ilike(f"%{q}%"), Product.is_active == True)
        .distinct()
        .limit(6)
    )
    result = await db.execute(query)
    rows = result.all()
    suggestions = [{"id": r.id, "name": r.name} for r in rows]
    return {"query": q, "suggestions": suggestions}


@router.post("/track", status_code=201)
async def track_product(
    body: TrackURLRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new product URL to track. Scrapes immediately."""
    VALID_RETAILERS = ["Amazon.in", "Flipkart", "Myntra", "Reliance Digital", "Nykaa", "Croma", "AJIO", "Tata CLiQ", "Meesho", "Snapdeal"]

    if body.retailer not in VALID_RETAILERS:
        raise HTTPException(status_code=400, detail=f"Unsupported retailer. Choose from: {VALID_RETAILERS}")

    product = await scraper_manager.add_product_from_url(body.url, body.retailer, db)
    if not product:
        raise HTTPException(status_code=422, detail="Could not scrape product. Check URL and try again.")

    # Trigger ML prediction in background
    background_tasks.add_task(run_prediction_for_product, product.id)

    return {
        "success": True,
        "message": f"Now tracking: {product.name}",
        "product": _product_dict(product),
    }


@router.post("/select")
async def select_product_candidate(
    body: ProductSelectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query_parts = [body.name, body.brand, body.model]
    refined_query = " ".join(p for p in query_parts if p).strip()
<<<<<<< HEAD
    results_payload = await scraper_manager.search_and_track(refined_query)
    results = _search_rows(results_payload)
    valid = [r for r in results if _row_is_valid(r)]
=======
    results = await scraper_manager.search_and_track(refined_query)
    valid = [r for r in results if r.is_valid]
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    if not valid:
        raise HTTPException(status_code=404, detail="No retailer listings found for the selected product")

    from app.scrapers.price_verifier import verify_retailer_prices
<<<<<<< HEAD
    urls = [_row_get(r, "url") for r in valid if _row_get(r, "url")]
=======
    urls = [r.url for r in valid if r.url]
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    verification = await verify_retailer_prices(urls)
    by_url = {v["url"]: v for v in verification}

    listings = []
    for r in valid:
<<<<<<< HEAD
        url = _row_get(r, "url")
        check = by_url.get(url, {})
        verified_price = check.get("verified_price")
        confidence = "high" if check.get("ok") and verified_price is not None else "low"
        listings.append({
            "retailer": _row_get(r, "retailer"),
            "url": url,
            "current_price": float(verified_price) if verified_price is not None else (float(_row_get(r, "current_price")) if _row_get(r, "current_price") else None),
            "serpapi_price": float(_row_get(r, "current_price")) if _row_get(r, "current_price") else None,
            "stock_status": bool(check.get("in_stock")) if check.get("in_stock") is not None else bool(_row_get(r, "in_stock")),
=======
        check = by_url.get(r.url, {})
        verified_price = check.get("verified_price")
        confidence = "high" if check.get("ok") and verified_price is not None else "low"
        listings.append({
            "retailer": r.retailer,
            "url": r.url,
            "current_price": float(verified_price) if verified_price is not None else (float(r.current_price) if r.current_price else None),
            "serpapi_price": float(r.current_price) if r.current_price else None,
            "stock_status": bool(check.get("in_stock")) if check.get("in_stock") is not None else bool(r.safe_in_stock),
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
            "verification_source": "scraperapi" if check.get("ok") else "serpapi",
            "verified_at": check.get("verified_at").isoformat() if check.get("verified_at") else None,
            "confidence": confidence,
        })
    return {"selection_id": body.selection_id, "query": refined_query, "retailers": listings}


@router.post("/search")
async def search_products(
    body: SearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_query = normalize_search_query(body.query)
    if len(normalized_query) < 2:
        raise HTTPException(status_code=400, detail="Query too short")

    # 1. Check if product already exists in DB to return instantly
    # We use slugify to match the search query to existing products
    from app.utils.slugify import slugify
    slug = slugify(normalized_query)
<<<<<<< HEAD
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.retailer_listings))
        .where(Product.slug == slug)
    )
=======
    result = await db.execute(select(Product).where(Product.slug == slug))
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    existing_product = result.scalar_one_or_none()

    if existing_product:
        # Return existing data immediately if fresh
        data = _product_dict(existing_product)
        # Check if stale
        stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)
        is_stale = not existing_product.retailer_listings or all(
            not l.last_scraped_at or l.last_scraped_at < stale_threshold 
            for l in existing_product.retailer_listings if l.is_active
        )
        if is_stale:
            # Force live refresh and wait
            await scraper_manager.refresh_product(existing_product.id)
            # Re-fetch the product to get fresh listings
            result = await db.execute(select(Product).options(selectinload(Product.retailer_listings)).where(Product.id == existing_product.id))
            existing_product = result.scalar_one_or_none()
        
        # Format for search result compatibility
        results_list = []
        for l in (existing_product.retailer_listings or []):
            if l.is_active:
                results_list.append({
                    "id":            existing_product.id,
                    "retailer":      l.retailer,
                    "url":           l.retailer_url,
<<<<<<< HEAD
                    "retailer_url":  l.retailer_url,
                    "buy_now_url":   l.retailer_url,
=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
                    "name":          existing_product.name,
                    "current_price": float(l.current_price) if l.current_price else None,
                    "mrp":           float(l.mrp)           if l.mrp           else None,
                    "in_stock":      l.safe_in_stock,
                    "image_url":     existing_product.image_url,
                })
        
        if results_list:
            return {"query": body.query, "results": results_list, "from_db": True}

<<<<<<< HEAD
    results_payload = await scraper_manager.search_and_track(normalized_query, body.retailers, body.category)
    results = _search_rows(results_payload)

    # Trigger background predictions for new products
    new_product_ids = {
        _row_get(r, "product_id") or _row_get(r, "id")
        for r in results
        if _row_get(r, "product_id") or _row_get(r, "id")
    }
=======
    results = await scraper_manager.search_and_track(normalized_query, body.retailers, body.category)

    # Trigger background predictions for new products
    new_product_ids = {r.product_id for r in results if r.product_id}
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    for pid in new_product_ids:
        background_tasks.add_task(run_prediction_for_product, pid)

    return {
        "query":   body.query,
        "results": [
            {
<<<<<<< HEAD
                "id":            _row_get(r, "product_id") or _row_get(r, "id"),
                "retailer":      _row_get(r, "retailer"),
                "url":           _row_get(r, "url"),
                "retailer_url":  _row_get(r, "url"),
                "buy_now_url":   _row_get(r, "url"),
                "name":          _row_get(r, "product_name") or _row_get(r, "name"),
                "current_price": float(_row_get(r, "current_price")) if _row_get(r, "current_price") else None,
                "mrp":           float(_row_get(r, "mrp")) if _row_get(r, "mrp") else None,
                "discount_pct":  float(_row_get(r, "discount_pct")) if _row_get(r, "discount_pct") else None,
                "in_stock":      bool(_row_get(r, "in_stock")),
                "image_url":     _row_get(r, "image_url"),
            }
            for r in results if _row_is_valid(r)
=======
                "id":            r.product_id, # Ensure ID is returned
                "retailer":      r.retailer,
                "url":           r.url,
                "name":          r.product_name,
                "current_price": float(r.current_price) if r.current_price else None,
                "mrp":           float(r.mrp)           if r.mrp           else None,
                "discount_pct":  float(r.discount_pct)  if r.discount_pct  else None,
                "in_stock":      r.safe_in_stock,
                "image_url":     r.image_url,
            }
            for r in results if r.is_valid
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
        ],
    }


@router.post("/public-search")
async def public_search_products(
    body: SearchRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Public search — no authentication required.
    - If query is a URL: scrape that exact URL (any site, including unknown ones).
    - If query is text: search across Amazon + Flipkart via live scraping.
    Advanced features (alerts, watchlist) still require login.
    """
    from app.models.system import RateLimitState
    from datetime import datetime, timezone, timedelta
    
    # ── Rate Limit ──
    limit_key = f"public:search:{request.client.host}"
    res = await db.execute(select(RateLimitState).where(RateLimitState.key == limit_key))
    state = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if state:
        elapsed = (now - state.last_triggered).total_seconds()
        if elapsed < 5: # 5s between public scans
             raise HTTPException(status_code=429, detail=f"Public search rate limit. Please wait {int(5-elapsed)}s or login for unlimited.")
        state.last_triggered = now
    else:
        db.add(RateLimitState(key=limit_key, last_triggered=now))
    await db.commit()

    # 1. Check if product already exists in DB to return instantly
    from app.utils.slugify import slugify
    normalized_query = normalize_search_query(body.query)
    slug = slugify(normalized_query)
<<<<<<< HEAD
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.retailer_listings))
        .where(Product.slug == slug)
    )
=======
    result = await db.execute(select(Product).where(Product.slug == slug))
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    existing_product = result.scalar_one_or_none()

    if existing_product:
        # Return existing data immediately if fresh
        stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)
        is_stale = not existing_product.retailer_listings or all(
            not l.last_scraped_at or l.last_scraped_at < stale_threshold 
            for l in existing_product.retailer_listings if l.is_active
        )
        if is_stale:
            # Force live refresh and wait
            await scraper_manager.refresh_product(existing_product.id)
            result = await db.execute(select(Product).options(selectinload(Product.retailer_listings)).where(Product.id == existing_product.id))
            existing_product = result.scalar_one_or_none()
        
        results_list = []
        for l in (existing_product.retailer_listings or []):
            if l.is_active:
                results_list.append({
                    "id":            existing_product.id,
                    "retailer":      l.retailer,
                    "url":           l.retailer_url,
<<<<<<< HEAD
                    "retailer_url":  l.retailer_url,
                    "buy_now_url":   l.retailer_url,
=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
                    "name":          existing_product.name,
                    "current_price": float(l.current_price) if l.current_price else None,
                    "mrp":           float(l.mrp)           if l.mrp           else None,
                    "in_stock":      l.safe_in_stock,
                    "image_url":     existing_product.image_url,
                })
        
        if results_list:
            return {"query": body.query, "results": results_list, "from_db": True}

    # 2. Live Scrape
    from urllib.parse import urlparse
    from app.scrapers.universal import universal_scraper

    q = normalized_query
    is_url = q.startswith("http://") or q.startswith("https://")

    if is_url:
        results = await universal_scraper.compare_from_url(q)
<<<<<<< HEAD
        results = [r for r in results if (r.get('is_valid') if isinstance(r, dict) else r.is_valid)]
    else:
        raw_results = _search_rows(await scraper_manager.search_and_track(q, body.retailers, body.category))
        results = [r for r in raw_results if _row_is_valid(r)]

    from app.models.product import RetailerListing
    urls = [r.get('url') if isinstance(r, dict) else r.url for r in results if (r.get('url') if isinstance(r, dict) else r.url)]
=======
        results = [r for r in results if r.is_valid]
    else:
        raw_results = await scraper_manager.search_and_track(q, body.retailers, body.category)
        results = [r for r in raw_results if r.is_valid]

    from app.models.product import RetailerListing
    urls = [r.url for r in results if r.url]
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    id_map = {}
    if urls:
        db_res = await db.execute(
            select(RetailerListing.retailer_url, RetailerListing.product_id)
            .where(RetailerListing.retailer_url.in_(urls))
        )
        for url_match, p_id in db_res.all():
            id_map[url_match] = p_id

    def _serial(r):
        return {
<<<<<<< HEAD
            "id":             id_map.get(_row_get(r, "url")) or _row_get(r, "product_id"),
            "retailer":       _row_get(r, "retailer"),
            "url":            _row_get(r, "url"),
            "retailer_url":   _row_get(r, "url"),
            "buy_now_url":    _row_get(r, "url"),
            "name":           _row_get(r, "product_name"),
            "current_price":  float(_row_get(r, "current_price")) if _row_get(r, "current_price") else None,
            "mrp":            float(_row_get(r, "mrp")) if _row_get(r, "mrp") else None,
            "discount_pct":   float(_row_get(r, "discount_pct")) if _row_get(r, "discount_pct") else None,
            "in_stock":       bool(_row_get(r, "in_stock")),
            "image_url":      _row_get(r, "image_url"),
            "specs":          _row_get(r, "specs", {}) or {},
            "brand":          _row_get(r, "brand"),
            "fetch_time_ms":  _row_get(r, "fetch_time_ms"),
            "fetch_method":   _row_get(r, "fetch_method"),
            "is_close_match": _row_get(r, "is_close_match", False),
=======
            "id":             id_map.get(r.url) or getattr(r, 'product_id', None),
            "retailer":       r.retailer,
            "url":            r.url,
            "name":           r.product_name,
            "current_price":  float(r.current_price) if r.current_price else None,
            "mrp":            float(r.mrp)           if r.mrp           else None,
            "discount_pct":   float(r.discount_pct)  if r.discount_pct  else None,
            "in_stock":       r.safe_in_stock,        # always bool, never None
            "image_url":      r.image_url,
            "specs":          getattr(r, "specs", {}) or {},
            "brand":          getattr(r, "brand", None),
            "fetch_time_ms":  getattr(r, "fetch_time_ms", None),
            "fetch_method":   getattr(r, "fetch_method", None),
            "is_close_match": getattr(r, "is_close_match", False),
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
        }

    return {
        "query":   q,
        "results": [_serial(r) for r in results],
    }


@router.get("/public-recent")
async def public_recent_products(
    db: AsyncSession = Depends(get_db),
):
    """
    Public access to recently tracked products with drops for landing page.
    """
    query = (
        select(Product)
        .options(selectinload(Product.retailer_listings))
        .where(Product.is_active == True)
        .order_by(desc(Product.created_at))
        .limit(3)
    )
    result = await db.execute(query)
    prods  = result.scalars().all()
    
    products_data = []
    for p in prods:
        d = _product_dict(p)
        latest_price = d.get("best_price")
        mrp = next((l.get("mrp") for l in d.get("retailers", []) if l.get("mrp")), None)
        drop_pct = int(((mrp - latest_price) / mrp) * 100) if mrp and latest_price and mrp > latest_price else 0
        d["drop_pct"] = drop_pct
        products_data.append(d)

    return {"data": products_data}

@router.get("/public-trending")
async def public_trending_products(
    db: AsyncSession = Depends(get_db),
):
    """
    Public access to trending products.
    """
    query = (
        select(Product)
        .options(selectinload(Product.retailer_listings))
        .where(Product.is_active == True)
        .order_by(Product.id)
        .limit(4)
    )
    result = await db.execute(query)
    prods  = result.scalars().all()
    
    products_data = []
    for p in prods:
        d = _product_dict(p)
        latest_price = d.get("best_price")
        mrp = next((l.get("mrp") for l in d.get("retailers", []) if l.get("mrp")), None)
        drop_pct = int(((mrp - latest_price) / mrp) * 100) if mrp and latest_price and mrp > latest_price else 0
        d["drop_pct"] = drop_pct
        products_data.append(d)

    return {"data": products_data}



@router.post("/compare-url")
async def compare_from_url(
    body: CompareURLRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Public URL comparison — paste any product URL, get prices from ALL retailers.
    No authentication required.

    Input:  { "url": "https://www.croma.com/apple-iphone-15/p/248765" }
    Output: Croma ₹79,900 + Amazon ₹77,990 + Flipkart ₹78,500 + Vijay Sales ₹76,990 ...

    Flow:
      1. Scrapes the pasted URL (any site — profile-based or universal fallback)
      2. Extracts product name from that page
      3. Runs full cross-retailer comparison:
         Engine 1: Known retailers (Amazon, Flipkart, Myntra etc.) via profiles
         Engine 2: Auto-discovery via Google Shopping (finds NEW retailers)
      4. Returns merged + deduplicated results sorted by price
    """
    from app.models.system import RateLimitState
    from datetime import datetime, timezone
    
    limit_key = f"public:compare:{request.client.host}"
    res = await db.execute(select(RateLimitState).where(RateLimitState.key == limit_key))
    state = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if state:
        elapsed = (now - state.last_triggered).total_seconds()
        if elapsed < 5:
             raise HTTPException(status_code=429, detail=f"Rate limit. Please wait {int(5-elapsed)}s.")
        state.last_triggered = now
    else:
        db.add(RateLimitState(key=limit_key, last_triggered=now))
    await db.commit()

    from app.scrapers.universal import universal_scraper

    url = body.url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="Must be a valid URL starting with http(s)://")

    def _s(r):
        return {
            "retailer":      r.retailer,
            "url":           r.url,
            "name":          r.product_name,
            "current_price": float(r.current_price) if r.current_price else None,
            "mrp":           float(r.mrp)           if r.mrp           else None,
            "discount_pct":  float(r.discount_pct)  if r.discount_pct  else None,
            "in_stock":      bool(r.safe_in_stock),
            "image_url":     r.image_url,
            "brand":         getattr(r, "brand", None),
        }

    results = await universal_scraper.compare_from_url(url)
    valid   = sorted(
        [r for r in results if r.is_valid],
        key=lambda r: r.current_price or 999999
    )

    return {
        "input_url": url,
        "detected_via": "url",
        "results": [_s(r) for r in valid],
    }


@router.post("/image-search")
async def image_search(
    request: Request,
    image: UploadFile     = File(...),
    db: AsyncSession     = Depends(get_db),
):
    """
    Public image search — no authentication required.

    Flow:
      1. Upload product photo
      2. Google Lens identifies product name
      3. Full cross-retailer comparison runs:
         Engine 1: Known retailers (Amazon, Flipkart, Myntra etc.) via profiles
         Engine 2: Auto-discovery via Google Shopping (any other retailer)
      4. Returns all retailers sorted by price
    """
    from app.scrapers.universal import universal_scraper
    from app.models.system import RateLimitState

    limit_key = f"public:image-search:{request.client.host}"
    res = await db.execute(select(RateLimitState).where(RateLimitState.key == limit_key))
    state = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if state:
        elapsed = (now - state.last_triggered).total_seconds()
        if elapsed < 10:
            raise HTTPException(status_code=429, detail=f"Image search rate limit. Please wait {int(10-elapsed)}s.")
        state.last_triggered = now
    else:
        db.add(RateLimitState(key=limit_key, last_triggered=now))
    await db.commit()

    image_bytes = await image.read()
    mime        = image.content_type or "image/jpeg"

    if len(image_bytes) < 100:
        raise HTTPException(status_code=400, detail="Image too small or empty")

    results = await universal_scraper.search_by_image(image_bytes, mime)
    valid   = sorted(
        [r for r in results if r.is_valid],
        key=lambda r: r.current_price or 999999
    )

    def _s(r):
        return {
            "retailer":      r.retailer,
            "url":           r.url,
            "name":          r.product_name,
            "current_price": float(r.current_price) if r.current_price else None,
            "mrp":           float(r.mrp)           if r.mrp           else None,
            "discount_pct":  float(r.discount_pct)  if r.discount_pct  else None,
            "in_stock":      bool(r.safe_in_stock),
            "image_url":     r.image_url,
            "brand":         getattr(r, "brand", None),
        }

    return {"results": [_s(r) for r in valid], "detected_via": "image"}



@router.get("/{product_id}")
async def get_product(
    product_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.retailer_listings),
            selectinload(Product.predictions),
        )
        .where(Product.id == product_id, Product.is_active == True)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

<<<<<<< HEAD
    await _seed_initial_price_history(db, product)

=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    # 1. Freshness Check (Auto-refresh if stale)
    stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=settings.CACHE_STALE_THRESHOLD_MINUTES)
    expire_threshold = datetime.now(timezone.utc) - timedelta(hours=settings.CACHE_EXPIRE_THRESHOLD_HOURS)
    listings = [l for l in (product.retailer_listings or []) if l.is_active]
    
    # If no listings OR most recent listing is older than 30 mins -> trigger refresh
    is_stale = not listings or all(not l.last_scraped_at or l.last_scraped_at < stale_threshold for l in listings)
    
    refresh_pending = False
    if is_stale:
        background_tasks.add_task(scraper_manager.refresh_product, product.id)
        refresh_pending = True
    if listings and all((not l.last_scraped_at or l.last_scraped_at < expire_threshold) for l in listings):
        await scraper_manager.refresh_product(product.id)
        refresh_pending = False

    data = _product_dict(product)
    data["is_stale"] = is_stale
    data["refresh_pending"] = refresh_pending

    # Attach latest prediction
    if product.predictions:
        latest = max(product.predictions, key=lambda p: p.predicted_at)
        data["prediction"] = {
            "predicted_price": float(latest.predicted_price),
            "predicted_low":   float(latest.predicted_low)   if latest.predicted_low  else None,
            "predicted_high":  float(latest.predicted_high)  if latest.predicted_high else None,
            "confidence":      float(latest.confidence)       if latest.confidence     else None,
            "horizon_days":    latest.horizon_days,
            "verdict":         latest.verdict,
            "reasoning":       latest.reasoning,
            "predicted_at":    latest.predicted_at.isoformat(),
        }

    return data


@router.post("/{product_id}/refresh")
async def refresh_product(
    product_id: int,
    background_tasks: BackgroundTasks,
    retailers: Optional[list[str]] = None,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Explicitly trigger a live market refresh for this product."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Retailer-scoped refresh currently falls back to full refresh path.
    background_tasks.add_task(scraper_manager.refresh_product, product.id)
    return {
        "success": True,
        "message": "Refresh task queued",
        "retailers_requested": retailers or "all",
        "refreshed_retailers": [],
    }


@router.get("/{product_id}/live-prices")
async def get_live_prices(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.system import RateLimitState

    result = await db.execute(
        select(Product).options(selectinload(Product.retailer_listings)).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    limit_key = f"product:live-prices:{product_id}:{request.client.host}"
    res = await db.execute(select(RateLimitState).where(RateLimitState.key == limit_key))
    state = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if state:
        elapsed = (now - state.last_triggered).total_seconds()
        if elapsed < 30:
            raise HTTPException(status_code=429, detail=f"Live price refresh rate limit. Try again in {int(30 - elapsed)}s.")
        state.last_triggered = now
    else:
        db.add(RateLimitState(key=limit_key, last_triggered=now))
    await db.commit()

    active = [l for l in (product.retailer_listings or []) if l.is_active and l.retailer_url]
    verified = await verify_retailer_prices([l.retailer_url for l in active])
    by_url = {v["url"]: v for v in verified}

    payload = []
    for listing in active:
        check = by_url.get(listing.retailer_url, {})
        verified_price = check.get("verified_price")
        listing.last_scraped_at = now
        if verified_price is not None:
            listing.current_price = verified_price
        if check.get("in_stock") is not None:
            listing.in_stock = bool(check["in_stock"])
<<<<<<< HEAD

        current_price = float(listing.current_price) if listing.current_price is not None else None
        if current_price is not None:
            mrp = float(listing.mrp) if listing.mrp else None
            discount_pct = None
            if mrp and mrp > 0:
                discount_pct = ((mrp - current_price) / mrp) * 100
            db.add(PriceHistory(
                product_id=product.id,
                listing_id=listing.id,
                retailer=listing.retailer,
                price=listing.current_price,
                mrp=listing.mrp,
                discount_pct=discount_pct,
                in_stock=listing.safe_in_stock,
                recorded_at=now,
            ))
        payload.append({
            "retailer": listing.retailer.value,
            "url": listing.retailer_url,
            "retailer_url": listing.retailer_url,
            "buy_now_url": listing.retailer_url,
=======
        payload.append({
            "retailer": listing.retailer.value,
            "url": listing.retailer_url,
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
            "current_price": float(listing.current_price) if listing.current_price else None,
            "verified_price": float(verified_price) if verified_price is not None else None,
            "verified_at": check.get("verified_at").isoformat() if check.get("verified_at") else None,
            "verification_source": "scraperapi" if check.get("ok") else "serpapi_fallback",
            "in_stock": bool(listing.safe_in_stock),
        })
    await db.commit()
    return {"product_id": product_id, "retailers": payload}


@router.get("/{product_id}/price-history")
async def get_price_history(
    product_id: int,
    days:       int          = Query(90, ge=1, le=730),
    retailer:   Optional[str]= Query(None),
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
<<<<<<< HEAD
    from collections import defaultdict
=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    from datetime import timedelta, timezone
    from datetime import datetime as dt

    since  = dt.now(timezone.utc) - timedelta(days=days)
    query  = (
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id, PriceHistory.recorded_at >= since)
        .order_by(PriceHistory.recorded_at)
    )
    if retailer:
        query = query.where(PriceHistory.retailer == RetailerName(retailer))

    result  = await db.execute(query)
    history = result.scalars().all()

<<<<<<< HEAD
    if not history:
        product_res = await db.execute(
            select(Product).options(selectinload(Product.retailer_listings)).where(Product.id == product_id)
        )
        product = product_res.scalar_one_or_none()
        if product:
            await _seed_initial_price_history(db, product)
            result = await db.execute(query)
            history = result.scalars().all()

    aggregated_map = {}
    retailer_map = defaultdict(list)

    for h in history:
        date_str = h.recorded_at.date().isoformat()
        price = float(h.price)
        retailer_name = h.retailer.value if hasattr(h.retailer, "value") else str(h.retailer)
        aggregated_map[date_str] = min(price, aggregated_map.get(date_str, price))
        retailer_map[retailer_name].append({
            "date": date_str,
            "price": price,
        })

    return {
        "aggregated": [
            {"date": date_str, "price": price}
            for date_str, price in sorted(aggregated_map.items())
        ],
        "retailers": dict(sorted(retailer_map.items())),
=======
    return {
        "product_id": product_id,
        "days":       days,
        "data": [
            {
                "price":       float(h.price),
                "mrp":         float(h.mrp) if h.mrp else None,
                "discount_pct":float(h.discount_pct) if h.discount_pct else None,
                "retailer":    h.retailer.value,
                "in_stock":    bool(h.safe_in_stock),
                "recorded_at": h.recorded_at.isoformat(),
            }
            for h in history
        ],
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    }


@router.post("/{product_id}/predict")
async def trigger_prediction(
    product_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger a fresh ML prediction for a product."""
    result  = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    background_tasks.add_task(run_prediction_for_product, product_id)
    return {"success": True, "message": "Prediction queued. Check back in a moment."}


@router.get("/{product_id}/prediction")
async def get_latest_prediction(
    product_id: int,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PricePrediction)
        .where(PricePrediction.product_id == product_id)
        .order_by(desc(PricePrediction.predicted_at))
        .limit(1)
    )
    pred = result.scalar_one_or_none()
    if not pred:
        raise HTTPException(status_code=404, detail="No prediction available yet")

    return {
        "predicted_price": float(pred.predicted_price),
        "predicted_low":   float(pred.predicted_low)  if pred.predicted_low  else None,
        "predicted_high":  float(pred.predicted_high) if pred.predicted_high else None,
        "confidence":      float(pred.confidence)      if pred.confidence     else None,
        "horizon_days":    pred.horizon_days,
        "verdict":         pred.verdict,
        "reasoning":       pred.reasoning,
        "model_version":   pred.model_version,
        "predicted_at":    pred.predicted_at.isoformat(),
    }


<<<<<<< HEAD
@router.post("/select/drill-down", response_model=dict)
async def select_and_drill_down(
    body: SelectionDrillDownRequest,
=======
@router.post("/select", response_model=dict)
async def select_and_drill_down(
    selection_id: str,
    query: str,
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Product drill-down endpoint.
    Takes a selection_id from lightweight search and triggers full scraping.
    Persists the product and returns detailed retailer listings.
    """
<<<<<<< HEAD
    selection_id = body.selection_id
    query = body.query
=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    import logging
    logger = logging.getLogger("uvicorn")
    
    from app.scrapers.manager import scraper_manager
    
    logger.info(f"[DrillDown] User {current_user.id} selecting product: {selection_id}")
    
    try:
        # Trigger full scraping and persistence
<<<<<<< HEAD
        results = _search_rows(await scraper_manager.search_and_track(query))
        
        # Find the selected product from results
        selected_product = None
        for result in results:
            if _row_get(result, "selection_id") == selection_id:
=======
        results = await scraper_manager.search_and_track(query)
        
        # Find the selected product from results
        selected_product = None
        for result in results.get("results", []):
            if result.get("selection_id") == selection_id:
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
                selected_product = result
                break
        
        if not selected_product:
            raise HTTPException(status_code=404, detail="Selected product not found")
        
        # Get the persisted product details
<<<<<<< HEAD
        product_name = _row_get(selected_product, "name")
=======
        product_name = selected_product.get("name")
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
        if not product_name:
            raise HTTPException(status_code=400, detail="Invalid product selection")
        
        # Find the persisted product in database
        from app.utils.slugify import slugify
        from app.models.product import Product
        from sqlalchemy.orm import selectinload
        
        slug = slugify(product_name)
        result = await db.execute(
            select(Product)
            .options(selectinload(Product.retailer_listings))
            .where(Product.slug == slug)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found after persistence")
        
        # Return detailed listings
        listings = []
        for listing in product.retailer_listings or []:
            if listing.is_active:
                listings.append({
                    "id": listing.id,
                    "retailer": listing.retailer.value,
                    "url": listing.retailer_url,
<<<<<<< HEAD
                    "retailer_url": listing.retailer_url,
                    "buy_now_url": listing.retailer_url,
                    "current_price": float(listing.current_price) if listing.current_price else None,
                    "mrp": float(listing.mrp) if listing.mrp else None,
                    "discount_pct": None,
                    "in_stock": bool(listing.safe_in_stock),
                    "image_url": None,
=======
                    "current_price": float(listing.current_price) if listing.current_price else None,
                    "mrp": float(listing.mrp) if listing.mrp else None,
                    "discount_pct": float(listing.discount_pct) if listing.discount_pct else None,
                    "in_stock": bool(listing.safe_in_stock),
                    "image_url": listing.image_url,
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
                    "last_scraped": listing.last_scraped_at.isoformat() if listing.last_scraped_at else None,
                })
        
        return {
            "product_id": product.id,
            "name": product.name,
            "slug": product.slug,
            "image_url": product.image_url,
            "brand": product.brand,
            "category": product.category,
            "created_at": product.created_at.isoformat(),
            "listings": listings,
            "total_listings": len(listings),
            "selection_id": selection_id,
            "drill_down_completed": True,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DrillDown] Failed for selection {selection_id}: {e}")
        raise HTTPException(status_code=500, detail="Drill-down failed. Please try again.")
