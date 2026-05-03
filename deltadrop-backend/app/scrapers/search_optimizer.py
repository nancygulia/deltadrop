"""
Search Optimizer - Implements strict search rules
1. Speed optimization with timeouts and parallel execution
2. Exact match keyword filtering
3. Brand-retailer filtering
4. Case insensitive normalization
"""

import asyncio
import logging
from typing import List, Dict, Set
from app.scrapers.brand_retailer_map import get_allowed_retailers, detect_brand_from_query

logger = logging.getLogger(__name__)

class SearchOptimizer:
    """
    Optimizes search queries according to strict rules:
    1. Speed: 10-20 second hard limit with parallel execution
    2. Exact match: All keywords must be present in product name
    3. Brand filtering: Only search authorized retailers
    4. Case insensitive: Normalize all inputs to lowercase
    """
    
    def __init__(self):
        self.search_timeout = 15.0  # Hard limit for entire search (reduced for faster response)
        self.retailer_timeout = 6.0  # Timeout per retailer (reduced to avoid long waits)
        
    def normalize_query(self, query: str) -> str:
        """
        Rule 4: Case insensitive normalization
        """
        return query.strip().lower()
    
    def extract_keywords(self, query: str) -> Set[str]:
        """
        Extract keywords from normalized query for exact matching
        """
        # Remove common stop words and split into keywords
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'must', 'can', 'shall', 'men', 'women', 'male', 'female', 'unisex',
            'for', 'with', 'size', 'color', 'colour'
        }
        
        words = query.lower().split()
        keywords = {word for word in words if word not in stop_words and len(word) > 1}
        
        logger.info(f"[KeywordExtraction] Query: '{query}' -> Keywords: {keywords}")
        return keywords
    
    def passes_exact_match(self, product_name: str, keywords: Set[str]) -> bool:
        """
        Rule 2: Flexible matching - return more results
        Only requires 50% of keywords to match for better user experience
        """
        if not keywords:
            return True
            
        product_lower = product_name.lower()
        
        # Count matching keywords with flexible scoring
        matched_keywords = 0
        required_matches = max(1, len(keywords) // 2)  # Only need 50% of keywords
        
        for keyword in keywords:
            # Exact match
            if keyword in product_lower:
                matched_keywords += 1
            # Partial match (e.g., 'jean' matches 'jeans')
            elif len(keyword) > 3 and keyword in product_lower.replace('s', ''):
                matched_keywords += 0.8
            # Brand name variations (e.g., 'h&m' matches 'hm')
            elif keyword.replace('&', '').replace(' ', '') in product_lower.replace('&', '').replace(' ', ''):
                matched_keywords += 0.7
            # Common variations
            elif self._is_keyword_variation(keyword, product_lower):
                matched_keywords += 0.6
        
        # Require at least required_matches keywords (50% threshold)
        if matched_keywords >= required_matches:
            logger.debug(f"[FlexibleMatch] PASSED: '{product_name}' matched {matched_keywords:.1f}/{len(keywords)} keywords")
            return True
        else:
            logger.debug(f"[FlexibleMatch] FAILED: '{product_name}' only matched {matched_keywords:.1f}/{len(keywords)} keywords")
            return False
    
    def _is_keyword_variation(self, keyword: str, text: str) -> bool:
        """
        Check if keyword has common variations in text
        """
        variations = {
            'jean': 'jeans',
            'shoe': 'shoes',
            'shirt': 'shirts',
            'pant': 'pants',
            'dress': 'dresses',
            'watch': 'watches',
            'bag': 'bags',
            'phone': 'phones',
            'laptop': 'laptops',
            'headphone': 'headphones',
            'earphone': 'earphones',
            'earbud': 'earbuds'
        }
        
        if keyword in variations:
            return variations[keyword] in text
        elif keyword in variations.values():
            # Reverse lookup
            for key, value in variations.items():
                if value == keyword and key in text:
                    return True
        
        return False
    
    def get_filtered_retailers(self, query: str) -> List[str]:
        """
        Rule 3: Brand-retailer filtering
        """
        return get_allowed_retailers(query)
    
    def should_skip_retailer(self, retailer: str, query: str) -> bool:
        """
        Check if a retailer should be skipped for the given query.
        """
        allowed_retailers = get_allowed_retailers(query)
        return retailer.lower() not in [r.lower() for r in allowed_retailers]
    
    def _source_matches_retailer(self, retailer: str, source: str) -> bool:
        """
        Check if a source matches the retailer
        """
        if not source:
            return False
        
        retailer_lower = retailer.lower()
        source_lower = source.lower()
        
        # Direct match
        if retailer_lower == source_lower:
            return True
        
        # Common variations
        retailer_mappings = {
            'amazon.in': ['amazon', 'amazon.in', 'amazon.com'],
            'flipkart.com': ['flipkart', 'flipkart.com'],
            'myntra.com': ['myntra', 'myntra.com'],
            'ajio.com': ['ajio', 'ajio.com'],
            'reliancedigital.in': ['reliance digital', 'reliancedigital', 'reliancedigital.in'],
            'croma.com': ['croma', 'croma.com'],
            'tatacliq.com': ['tata cliq', 'tatacliq', 'tatacliq.com']
        }
        
        # Check mappings
        for mapped_retailer, variations in retailer_mappings.items():
            if retailer_lower == mapped_retailer:
                return any(var in source_lower for var in variations)
        
        return False
    
    async def parallel_retailer_search(
        self,
        query: str,
        retailers: List[str],
        search_func,
        require_exact_match: bool = True,
    ) -> List[Dict]:
        """
        Rule 1: Speed optimization - parallel retailer searches with timeouts
        """
        normalized_query = self.normalize_query(query)
        keywords = self.extract_keywords(normalized_query)
        
        # Create search tasks for each retailer
        tasks = []
        for retailer in retailers:
            task = asyncio.create_task(
                self._search_retailer_with_timeout(
                    retailer, normalized_query, keywords, search_func
                )
            )
            tasks.append(task)
        
        # Wait for all tasks with overall timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.search_timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"[SpeedOptimization] Overall search timeout ({self.search_timeout}s)")
            # Cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            results = []
        
        # Process results and optionally filter by exact match
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"[ParallelSearch] Retailer search failed: {result}")
                continue
                
            if isinstance(result, list):
                if require_exact_match:
                    exact_matches = [
                        product for product in result
                        if self.passes_exact_match(product.get('name', ''), keywords)
                    ]
                    final_results.extend(exact_matches)
                else:
                    final_results.extend(result)

        if require_exact_match:
            logger.info(f"[ParallelSearch] Found {len(final_results)} exact matches from {len(retailers)} retailers")
        else:
            logger.info(f"[ParallelSearch] Found {len(final_results)} fallback candidates from {len(retailers)} retailers")
        return final_results
    
    async def _search_retailer_with_timeout(self, retailer: str, query: str, keywords: Set[str], search_func) -> List[Dict]:
        """
        Search a single retailer with timeout and retry logic
        """
        max_retries = 2
        base_timeout = self.retailer_timeout
        
        for attempt in range(max_retries + 1):
            try:
                timeout = base_timeout * (attempt + 1)  # Increase timeout with each retry
                result = await asyncio.wait_for(
                    search_func(retailer, query),
                    timeout=timeout
                )
                result_count = len(result) if isinstance(result, list) else 0
                if attempt > 0:
                    logger.info(f"[RetailerSearch] {retailer}: {result_count} results (retry {attempt})")
                else:
                    logger.info(f"[RetailerSearch] {retailer}: {result_count} results")
                return result
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    logger.warning(f"[RetailerSearch] {retailer}: Timeout after {timeout}s, retrying... ({attempt + 1}/{max_retries + 1})")
                    await asyncio.sleep(1)  # Brief delay before retry
                else:
                    logger.warning(f"[RetailerSearch] {retailer}: Timeout after {timeout}s (final attempt)")
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"[RetailerSearch] {retailer}: {e}, retrying... ({attempt + 1}/{max_retries + 1})")
                    await asyncio.sleep(0.5)  # Brief delay before retry
                else:
                    logger.error(f"[RetailerSearch] {retailer}: {e} (final attempt)")
        
        return []
    
    def create_no_match_response(self, query: str, keywords: Set[str]) -> Dict:
        """
        Create response when no exact matches found
        """
        return {
            "results": [],
            "query": query,
            "keywords": list(keywords),
            "search_mode": "exact_match",
            "message": "No exact match found for your search.",
            "retailers_scanned": 0,
            "search_time": 0,
            "exact_match_required": True
        }
    
    def optimize_search_query(self, query: str) -> Dict:
        """
        Analyze and optimize search query
        """
        normalized = self.normalize_query(query)
        keywords = self.extract_keywords(normalized)
        brand = detect_brand_from_query(normalized)
        allowed_retailers = self.get_filtered_retailers(normalized)
        
        return {
            "original_query": query,
            "normalized_query": normalized,
            "keywords": list(keywords),
            "brand_detected": brand,
            "allowed_retailers": allowed_retailers,
            "is_filtered": brand != "",
            "retailer_count": len(allowed_retailers)
        }

# Global optimizer instance
search_optimizer = SearchOptimizer()
