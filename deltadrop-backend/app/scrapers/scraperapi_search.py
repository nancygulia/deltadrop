"""
ScraperAPI Search Service - Enhanced Product Discovery
=================================================
Uses ScraperAPI for robust product search across multiple retailers.
Bypasses anti-bot measures and provides reliable results.
"""
import asyncio
import hashlib
import logging
import re
from typing import List, Dict, Optional
from urllib.parse import urlencode, quote_plus

from app.core.config import settings
from app.scrapers.smart_http import _fetch_scraperapi, _scraperapi_semaphore

logger = logging.getLogger(__name__)


class ScraperAPISearch:
    """
    Enhanced search service using ScraperAPI for product discovery.
    """
    
    def __init__(self):
        self.api_key = settings.SCRAPER_API_KEY
        
    async def search_products(self, query: str, limit: int = 12) -> List[Dict]:
        """
        Search for products using ScraperAPI with multiple search strategies.
        """
        if not self.api_key or "placeholder" in self.api_key.lower() or "your_" in self.api_key.lower():
            logger.warning("[ScraperAPISearch] No valid API key configured")
            return []
            
        logger.info(f"[ScraperAPISearch] Searching for: '{query}' (limit: {limit})")
        
        # Try multiple search strategies in parallel
        search_tasks = [
            self._search_google_shopping(query, limit),
            self._search_amazon(query, limit // 2),
            self._search_flipkart(query, limit // 2),
        ]
        
        results = []
        try:
            # Execute searches in parallel with semaphore limit
            async with _scraperapi_semaphore:
                search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
                
                # Collect and merge results
                all_products = []
                for i, search_result in enumerate(search_results):
                    if isinstance(search_result, Exception):
                        logger.warning(f"[ScraperAPISearch] Search strategy {i} failed: {search_result}")
                        continue
                    all_products.extend(search_result)
                
                # Deduplicate by product name similarity
                seen_names = set()
                for product in all_products:
                    name_key = self._normalize_name(product.get("name", ""))
                    if name_key not in seen_names and len(all_products) < limit:
                        seen_names.add(name_key)
                        results.append(product)
                        
        except Exception as e:
            logger.error(f"[ScraperAPISearch] Search failed: {e}")
            
        logger.info(f"[ScraperAPISearch] Found {len(results)} unique products")
        return results[:limit]
    
    async def _search_google_shopping(self, query: str, limit: int) -> List[Dict]:
        """
        Search Google Shopping using ScraperAPI.
        """
        try:
            search_url = f"https://www.google.com/search?tbm=shop&q={quote_plus(query)}"
            html = await _fetch_scraperapi(search_url)
            
            if not html:
                return []
                
            return self._parse_google_shopping(html, limit)
            
        except Exception as e:
            logger.warning(f"[ScraperAPISearch] Google Shopping search failed: {e}")
            return []
    
    async def _search_amazon(self, query: str, limit: int) -> List[Dict]:
        """
        Search Amazon.in using ScraperAPI.
        """
        try:
            search_url = f"https://www.amazon.in/s?k={quote_plus(query)}"
            html = await _fetch_scraperapi(search_url)
            
            if not html:
                return []
                
            return self._parse_amazon(html, limit)
            
        except Exception as e:
            logger.warning(f"[ScraperAPISearch] Amazon search failed: {e}")
            return []
    
    async def _search_flipkart(self, query: str, limit: int) -> List[Dict]:
        """
        Search Flipkart using ScraperAPI.
        """
        try:
            search_url = f"https://www.flipkart.com/search?q={quote_plus(query)}"
            html = await _fetch_scraperapi(search_url)
            
            if not html:
                return []
                
            return self._parse_flipkart(html, limit)
            
        except Exception as e:
            logger.warning(f"[ScraperAPISearch] Flipkart search failed: {e}")
            return []
    
    def _parse_google_shopping(self, html: str, limit: int) -> List[Dict]:
        """
        Parse Google Shopping results from HTML.
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        products = []
        
        # Google Shopping product containers
        for item in soup.select("div.shSERP")[:limit]:
            try:
                name_elem = item.select_one("h3.tAxDx")
                price_elem = item.select_one("span.a8Pemb")
                img_elem = item.select_one("img.XS5d")
                source_elem = item.select_one("div.E5ocAb")
                
                if not name_elem:
                    continue
                    
                name = name_elem.get_text(strip=True)
                price_text = price_elem.get_text(strip=True) if price_elem else ""
                price = self._parse_price(price_text)
                image = img_elem.get("src") if img_elem else None
                source = source_elem.get_text(strip=True) if source_elem else "Google Shopping"
                
                products.append({
                    "selection_id": hashlib.sha1(f"{name}|{source}".encode("utf-8")).hexdigest()[:20],
                    "name": name,
                    "approximate_price": price,
                    "price_range": {"min": price, "max": price} if price else None,
                    "image": image,
                    "retailer_sources": [source],
                    "search_source": "scraperapi_google",
                })
            except Exception as e:
                logger.debug(f"[ScraperAPISearch] Error parsing Google Shopping item: {e}")
                continue
                
        return products
    
    def _parse_amazon(self, html: str, limit: int) -> List[Dict]:
        """
        Parse Amazon search results from HTML.
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        products = []
        
        # Amazon product containers
        for item in soup.select("div[data-component-type='s-search-result']")[:limit]:
            try:
                name_elem = item.select_one("h2.a-size-mini")
                price_elem = item.select_one("span.a-price-whole")
                img_elem = item.select_one("img.s-image")
                
                if not name_elem:
                    continue
                    
                name = name_elem.get_text(strip=True)
                price_text = price_elem.get_text(strip=True) if price_elem else ""
                price = self._parse_price(price_text)
                image = img_elem.get("src") if img_elem else None
                
                products.append({
                    "selection_id": hashlib.sha1(f"{name}|Amazon".encode("utf-8")).hexdigest()[:20],
                    "name": name,
                    "approximate_price": price,
                    "price_range": {"min": price, "max": price} if price else None,
                    "image": image,
                    "retailer_sources": ["Amazon"],
                    "search_source": "scraperapi_amazon",
                })
            except Exception as e:
                logger.debug(f"[ScraperAPISearch] Error parsing Amazon item: {e}")
                continue
                
        return products
    
    def _parse_flipkart(self, html: str, limit: int) -> List[Dict]:
        """
        Parse Flipkart search results from HTML.
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        products = []
        
        # Flipkart product containers
        for item in soup.select("div._1AtVbE")[:limit]:
            try:
                name_elem = item.select_one("div.tUxRFH")
                price_elem = item.select_one("div.Nx9bqj")
                img_elem = item.select_one("img.DByuf4")
                
                if not name_elem:
                    continue
                    
                name = name_elem.get_text(strip=True)
                price_text = price_elem.get_text(strip=True) if price_elem else ""
                price = self._parse_price(price_text)
                image = img_elem.get("src") if img_elem else None
                
                products.append({
                    "selection_id": hashlib.sha1(f"{name}|Flipkart".encode("utf-8")).hexdigest()[:20],
                    "name": name,
                    "approximate_price": price,
                    "price_range": {"min": price, "max": price} if price else None,
                    "image": image,
                    "retailer_sources": ["Flipkart"],
                    "search_source": "scraperapi_flipkart",
                })
            except Exception as e:
                logger.debug(f"[ScraperAPISearch] Error parsing Flipkart item: {e}")
                continue
                
        return products
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """
        Extract numeric price from text.
        """
        if not price_text:
            return None
            
        # Remove currency symbols and extract numbers
        cleaned = re.sub(r'[^\d.]', '', price_text.replace(',', ''))
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize product name for deduplication.
        """
        if not name:
            return ""
        # Remove common variations and normalize
        normalized = re.sub(r'[^a-zA-Z0-9\s]', '', name.lower())
        return re.sub(r'\s+', ' ', normalized).strip()


# Global instance
scraperapi_search = ScraperAPISearch()
