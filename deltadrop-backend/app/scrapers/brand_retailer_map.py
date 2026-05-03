"""
Brand-to-Retailer Mapping System
Maps specific brands to their authorized retailers for targeted search.
"""

from typing import Dict, List, Set
import logging

logger = logging.getLogger(__name__)

# Brand to authorized retailer mapping
BRAND_RETAILER_MAP: Dict[str, List[str]] = {
    # Fashion brands that primarily sell on specific retailers
    "h&m": ["myntra.com", "ajio.com", "hm.com"],
    "hm": ["myntra.com", "ajio.com", "hm.com"],
    
    # Premium fashion brands
    "zara": ["zara.com", "myntra.com", "ajio.com"],
    "uniqlo": ["uniqlo.com", "myntra.com", "ajio.com"],
    
    # Beauty & personal care
    "mamaearth": ["mamaearth.in", "nykaa.com", "amazon.in"],
    "mcaffeine": ["mcaffeine.com", "nykaa.com", "amazon.in"],
    "minimalist": ["minimalist.in", "nykaa.com", "amazon.in"],
    
    # Electronics (allow Amazon + Flipkart + brand sites)
    "boat": ["boat-lifestyle.com", "amazon.in", "flipkart.com", "reliancedigital.in"],
    "boAt": ["boat-lifestyle.com", "amazon.in", "flipkart.com", "reliancedigital.in"],
    "samsung": ["samsung.com", "amazon.in", "flipkart.com", "reliancedigital.in", "croma.com"],
    "apple": ["apple.com", "amazon.in", "flipkart.com", "reliancedigital.in", "croma.com"],
    "oneplus": ["oneplus.com", "amazon.in", "flipkart.com", "reliancedigital.in"],
    "xiaomi": ["mi.com", "amazon.in", "flipkart.com", "reliancedigital.in"],
    
    # Sports brands
    "nike": ["nike.com", "amazon.in", "flipkart.com", "ajio.com"],
    "adidas": ["adidas.com", "amazon.in", "flipkart.com", "ajio.com"],
    "puma": ["puma.com", "amazon.in", "flipkart.com", "ajio.com"],
    
    # Jewelry
    "tanishq": ["tanishq.co.in"],
    "caratlane": ["caratlane.com", "amazon.in"],
    
    # Eyewear
    "lenskart": ["lenskart.com", "amazon.in", "flipkart.com"],
    
    # Home & furniture
    "ikea": ["ikea.com", "amazon.in"],
    "pepperfry": ["pepperfry.com", "amazon.in"],
    
    # Grocery & essentials
    "bigbasket": ["bigbasket.com"],
    "blinkit": ["blinkit.com"],
    "zepto": ["zepto.com"],
}

# All available retailers in the system
ALL_RETAILERS = [
    "amazon.in",
    "flipkart.com", 
    "myntra.com",
    "ajio.com",
    "reliancedigital.in",
    "nykaa.com",
    "tatacliq.com",
    "croma.com",
    "vijaysales.com",
    "samsung.com",
    "apple.com",
    "boat-lifestyle.com",
    "mamaearth.in",
    "minimalist.in",
    "mcaffeine.com",
    "thesouledstore.com",
    "bewakoof.com",
    "lenskart.com",
    "tanishq.co.in",
    "hm.com",
    "zara.com",
    "uniqlo.com",
    "nike.com",
    "adidas.com",
    "puma.com",
    "oneplus.com",
    "mi.com",
    "ikea.com",
    "pepperfry.com",
    "caratlane.com",
    "bigbasket.com",
    "blinkit.com",
    "zepto.com"
]

def detect_brand_from_query(query: str) -> str:
    """
    Detect brand name from search query.
    Returns lowercase brand name or empty string if no brand detected.
    """
    query_lower = query.lower()
    
    # Check for exact brand matches first
    for brand in BRAND_RETAILER_MAP.keys():
        if brand.lower() in query_lower:
            logger.info(f"[BrandDetection] Detected brand: {brand} from query: {query}")
            return brand.lower()
    
    # Check for common brand variations
    brand_keywords = {
        "h and m": "h&m",
        "h&m": "h&m",
        "hm": "h&m",
        "boat": "boat",
        "bo at": "boat",
        "samsung": "samsung",
        "apple iphone": "apple",
        "iphone": "apple",
        "nike": "nike",
        "adidas": "adidas",
        "puma": "puma",
        "zara": "zara",
        "uniqlo": "uniqlo",
        "myntra": "myntra",
        "ajio": "ajio",
        "tanishq": "tanishq",
        "lenskart": "lenskart",
        "oneplus": "oneplus",
        "xiaomi": "xiaomi",
        "mi": "xiaomi",
        "ikea": "ikea",
        "mamaearth": "mamaearth",
        "mcaffeine": "mcaffeine",
        "minimalist": "minimalist",
    }
    
    for keyword, brand in brand_keywords.items():
        if keyword in query_lower:
            logger.info(f"[BrandDetection] Detected brand: {brand} from keyword: {keyword}")
            return brand
    
    return ""

def get_allowed_retailers(query: str) -> List[str]:
    """
    Get list of allowed retailers for a given query based on brand detection.
    If no brand detected, return all retailers.
    """
    brand = detect_brand_from_query(query)
    
    if brand and brand in BRAND_RETAILER_MAP:
        allowed = BRAND_RETAILER_MAP[brand]
        logger.info(f"[BrandFilter] Brand '{brand}' -> Allowed retailers: {allowed}")
        return allowed
    
    # No brand detected or unknown brand -> search all retailers
    logger.info(f"[BrandFilter] No brand filter -> Using all {len(ALL_RETAILERS)} retailers")
    return ALL_RETAILERS.copy()

def should_skip_retailer(retailer: str, query: str) -> bool:
    """
    Check if a retailer should be skipped for the given query.
    """
    allowed_retailers = get_allowed_retailers(query)
    return retailer.lower() not in [r.lower() for r in allowed_retailers]

def get_brand_info(query: str) -> Dict:
    """
    Get comprehensive brand information for a query.
    """
    brand = detect_brand_from_query(query)
    allowed_retailers = get_allowed_retailers(query)
    
    return {
        "brand_detected": brand,
        "allowed_retailers": allowed_retailers,
        "is_filtered": brand != "",
        "total_available": len(ALL_RETAILERS),
        "filtered_count": len(allowed_retailers)
    }
