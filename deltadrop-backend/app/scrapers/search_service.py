from app.scrapers.serpapi import serpapi_scraper
from app.scrapers.universal import universal_scraper
from app.scrapers.scraperapi_search import scraperapi_search
from app.scrapers.search_optimizer import search_optimizer
from app.core.config import settings
import logging
import time
from typing import List, Dict

logger = logging.getLogger(__name__)


class ProductSearchService:
    """
    Original search service - delegates to scraper_manager for full discovery and persistence.
    """
    
    async def search_products(self, query: str, limit: int = 12) -> dict:
        """
        Original search implementation - delegates to scraper_manager
        """
        from app.scrapers.manager import scraper_manager
        import time
        import asyncio
        
        start_time = time.time()
        
        try:
            # Use scraper_manager for search
            results = await scraper_manager.accurate_search(query)
            
            search_time = time.time() - start_time
            
            return {
                "results": results,
                "query": query,
                "original_query": query,
                "search_time": search_time,
                "search_mode": "scraper_manager",
                "total_found": len(results),
                "returned": len(results),
                "message": f"Found {len(results)} products for '{query}'"
            }
            
        except Exception as e:
            logger.error(f"[SearchService] Search failed: {e}")
            search_time = time.time() - start_time
            
            # Try emergency fallback
            try:
                from emergency_search_fallback import emergency_search
                logger.warning(f"[SearchService] Using emergency fallback for '{query}'")
                emergency_result = await emergency_search.search_products(query, limit=10)
                emergency_result["search_time"] = search_time
                emergency_result["original_query"] = query
                return emergency_result
            except Exception as fallback_error:
                logger.error(f"[SearchService] Emergency fallback also failed: {fallback_error}")
                
                # Return empty results as last resort
                return {
                    "results": [],
                    "query": query,
                    "original_query": query,
                    "search_time": search_time,
                "search_mode": "error",
                "total_found": 0,
                "returned": 0,
                "message": f"Search failed: {str(e)}"
            }


# Global instance
product_search_service = ProductSearchService()
