"""
Identity Resolver — The "Google Brain" of DeltaDrop.
===================================================
Resolves raw user input (Images, Names, URLs) into a Canonical Product Identity.

Input:  "adidas ub5" or a product URL or an image filename.
Output: {
    "canonical_name": "Adidas Ultraboost 5 Men's Running Shoes",
    "brand": "Adidas",
    "category": "Shoes > Men's Sneakers",
    "msrp_estimate": 16999,
    "confidence": 0.95
}
"""
import logging
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from app.scrapers.base import BaseScraper
from app.scrapers.site_profiles import detect_platform

logger = logging.getLogger(__name__)

class IdentityResolver:
    def __init__(self, scraper: BaseScraper):
        self.scraper = scraper

    async def resolve(self, query: str, preferred_category: Optional[str] = None) -> Dict[str, Any]:
        """
        Main entry point for product identity resolution.
        """
        logger.info(f"[Identity] Resolving: {query}")
        
        # 1. Detect if input is a URL
        if re.match(r'^https?://', query):
            return await self._resolve_url(query)
            
        # 2. Detect if input is a descriptive image name (e.g. adidas_ub5.jpg)
        if re.search(r'\.(jpg|jpeg|png|webp|gif|bmp)$', query, re.I):
            clean_query = self._clean_filename(query)
            return await self._resolve_text(clean_query, preferred_category)
            
        # 3. Default: Text search resolution
        return await self._resolve_text(query, preferred_category)

    async def _resolve_text(self, text: str, preferred_category: Optional[str]) -> Dict[str, Any]:
        """
        Use Google Search / Shopping to find the "Official" name and category.
        """
        # Step A: Query Google for Identity (we use udm=28 for shopping-rich results)
        # Or a broad search to find the official brand page
        search_query = f"{text} official product name brand MSRP"
        if preferred_category:
            search_query += f" {preferred_category}"
            
        # We use a dedicated scraper instance (ScraperAPI) to fetch the Google Search result
        # For development, we'll use a mocked/heuristic approach if ScraperAPI fails
        url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
        
        try:
            # We fetch with a high tier to ensure we get JS-rendered snippets
            html, method, _ = await self.scraper.fetch_html_with_fallback(url)
            if not html:
                return self._stub_resolution(text, preferred_category)
                
            return self._parse_google_identity(html, text, preferred_category)
        except Exception as e:
            logger.error(f"[Identity] Resolution error: {e}")
            return self._stub_resolution(text, preferred_category)

    async def _resolve_url(self, url: str) -> Dict[str, Any]:
        """
        Scrape the direct URL to get high-fidelity identity data.
        """
        try:
            res = await self.scraper.scrape_url(url)
            if res and res.product_name:
                return {
                    "canonical_name": res.product_name,
                    "brand": res.brand or res.product_name.split()[0],
                    "category": None, # Will be detected from name later
                    "msrp_estimate": res.mrp or res.current_price,
                    "confidence": 1.0,
                    "source_url": url
                }
        except Exception:
            pass
        return self._stub_resolution(url)

    def _parse_google_identity(self, html: str, original_query: str, preferred_category: Optional[str]) -> Dict[str, Any]:
        """
        Extract identity markers from Google SERP (Rich snippets, People also ask, etc.)
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Try to find the official title from the first few rich snippets
        # Google Shopping results often have structured cards
        h3s = [h.get_text() for h in soup.select("h3")][:5]
        
        # Heuristic: The most frequent words in top titles + original query
        canonical_name = h3s[0] if h3s else original_query
        
        # 2. Detect category from breadcrumbs
        category = "Unknown"
        breadcrumb = soup.select_one(".Z26q7c") # Common breadcrumb class
        if breadcrumb:
            category = breadcrumb.get_text(" > ")

        # 3. Detect MSRP
        msrp = None
        price_matches = re.findall(r'₹\s?([\d,]+)', html)
        if price_matches:
            # Clean and convert to int
            prices = [int(p.replace(',', '')) for p in price_matches]
            msrp = max(prices) if prices else None

        return {
            "canonical_name": canonical_name,
            "brand": canonical_name.split()[0] if canonical_name else "Unknown",
            "category": category,
            "msrp_estimate": msrp,
            "confidence": 0.8
        }

    def _clean_filename(self, filename: str) -> str:
        """Converts img_adidas_ub5.jpg -> adidas ub5"""
        name = filename.split('.')[0]
        # Remove common prefixes/suffixes
        name = re.sub(r'^(img|product|image|photo)[_-]', '', name, flags=re.I)
        name = re.sub(r'[_-]large|[_-]thumb|[_-]v\d+', '', name, flags=re.I)
        # Replace dashes/underscores with spaces
        return name.replace('_', ' ').replace('-', ' ').strip()

    def _stub_resolution(self, text: str, category: Optional[str] = None) -> Dict[str, Any]:
        """Fallback when Google is blocked or fails."""
        return {
            "canonical_name": text,
            "brand": text.split()[0] if text else "Unknown",
            "category": category or "Unknown",
            "msrp_estimate": None,
            "confidence": 0.5
        }
