from app.scrapers.serpapi import serpapi_scraper
from app.scrapers.universal import universal_scraper
from app.scrapers.scraperapi_search import scraperapi_search
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class ProductSearchService:
    """
    Enhanced search service for broad product discovery.
    Uses multiple search strategies: SerpAPI -> ScraperAPI -> UniversalScraper.
    All results are transient (no DB persistence) until user selection.
    """
    
    async def search_products(self, query: str, limit: int = 12) -> list[dict]:
        """
        Multi-strategy search mode for product discovery.
        Tries best available search method in priority order.
        """
        # Check API key availability
        has_serpapi = settings.SERPAPI_API_KEY and "placeholder" not in settings.SERPAPI_API_KEY.lower() and "your_" not in settings.SERPAPI_API_KEY.lower()
        has_scraperapi = settings.SCRAPER_API_KEY and "placeholder" not in settings.SCRAPER_API_KEY.lower() and "your_" not in settings.SCRAPER_API_KEY.lower()
        
        candidates = []
        search_source = "none"
        
        # Priority 1: SerpAPI (Google Shopping - most comprehensive)
        if has_serpapi:
            logger.info("[SearchService] Trying SerpAPI search")
            candidates = await serpapi_scraper.search_candidates(query, limit=limit)
            if candidates:
                search_source = "serpapi"
                logger.info(f"[SearchService] SerpAPI returned {len(candidates)} results")
        
        # Priority 2: ScraperAPI (robust multi-retailer search)
        if not candidates and has_scraperapi:
            logger.info("[SearchService] Trying enhanced ScraperAPI search")
            try:
                candidates = await scraperapi_search.search_products(query, limit=limit)
                if candidates:
                    search_source = "scraperapi_enhanced"
                    logger.info(f"[SearchService] Enhanced ScraperAPI returned {len(candidates)} results")
            except Exception as e:
                logger.error(f"[SearchService] Enhanced ScraperAPI search failed: {e}")
        
        # Priority 3: UniversalScraper with ScraperAPI fallback
        if not candidates and has_scraperapi:
            logger.info("[SearchService] Trying UniversalScraper with ScraperAPI")
            try:
                fallback_results = await universal_scraper.search_by_name(query)
                if fallback_results and fallback_results.get("results"):
                    candidates = self._convert_universal_results(fallback_results["results"][:limit], "scraperapi_universal")
                    search_source = "scraperapi_universal"
                    logger.info(f"[SearchService] Universal+ScraperAPI returned {len(candidates)} results")
            except Exception as e:
                logger.error(f"[SearchService] Universal+ScraperAPI search failed: {e}")
        
        # Priority 4: Basic UniversalScraper (no API keys)
        if not candidates:
            logger.warning("[SearchService] No API keys working, trying basic search")
            try:
                fallback_results = await universal_scraper.search_by_name(query)
                if fallback_results and fallback_results.get("results"):
                    candidates = self._convert_universal_results(fallback_results["results"][:limit], "basic")
                    search_source = "basic"
                    logger.info(f"[SearchService] Basic search returned {len(candidates)} results")
            except Exception as e:
                logger.error(f"[SearchService] Basic search failed: {e}")
        
        # Add metadata for frontend consumption
        for candidate in candidates:
            candidate["is_transient"] = True
            candidate["search_source"] = search_source
            candidate["requires_drilldown"] = True
            candidate["is_fallback"] = search_source not in ["serpapi", "scraperapi_enhanced"]
            
            # Set search mode based on source
            if search_source == "serpapi":
                candidate["search_mode"] = "lightweight"
            elif "scraperapi" in search_source:
                candidate["search_mode"] = "scraperapi"
            else:
                candidate["search_mode"] = "fallback"
        
        return candidates
    
    def _convert_universal_results(self, results: list, source: str) -> list[dict]:
        """
        Convert UniversalScraper results to candidate format.
        """
        converted = []
        for i, result in enumerate(results):
            candidate = {
                "selection_id": f"{source}_{i}_{hash(result.get('product_name', '')) % 10000}",
                "name": result.get("product_name", ""),
                "image": result.get("image_url"),
                "approximate_price": float(result.get("current_price", 0)) if result.get("current_price") else None,
                "price_range": {"min": float(result.get("current_price", 0)), "max": float(result.get("current_price", 0))} if result.get("current_price") else None,
                "retailer_sources": [result.get("retailer", "Unknown")],
                "search_source": source,
            }
            converted.append(candidate)
        return converted
    
    async def quick_search(self, query: str, limit: int = 8) -> list[dict]:
        """
        Even faster search mode with fewer results for autocomplete/suggestions.
        """
        return await self.search_products(query, limit=limit)
product_search_service = ProductSearchService()
