"""
Category Router
===============
Solves Question 3: "H&M is on Myntra/Ajio, not on Amazon/Flipkart — 
don't search Amazon for H&M products."

Responsibilities:
  1. Detect product CATEGORY from query (electronics, fashion, beauty etc.)
  2. Filter RELEVANT RETAILERS for that category
     → Skip Amazon for fashion. Skip Myntra for electronics.
  3. Detect BRAND WEBSITE from query
     → "Nike Air Max" → also include nike.com
     → "boAt Airdopes" → also include boat-lifestyle.com
  4. Extract PRODUCT SPECS/METADATA from query
     → "H&M T-Shirt Size M" → { size: "M" }
     → "Minimalist Vitamin C 10% 30ml" → { volume: "30ml", concentration: "10%" }
     → "Samsung Galaxy S24 8GB 256GB" → { ram: "8GB", storage: "256GB" }

This ensures:
  - No garbage results (H&M on Amazon = wrong product)  
  - Brand website always included in comparison
  - Metadata passed to frontend for filter chips in UI
"""
import re
from typing import Optional

# ── Category definitions ──────────────────────────────────────────────────────

CATEGORIES = {
    "electronics": {
        "keywords": [
            "phone", "iphone", "samsung", "oneplus", "pixel", "redmi", "realme", "poco", "motorola",
            "laptop", "macbook", "notebook", "chromebook", "ultrabook",
            "headphone", "earphone", "earbuds", "airpods", "speaker", "soundbar",
            "tv", "television", "oled", "qled", "smarttv",
            "tablet", "ipad", "kindle",
            "camera", "dslr", "mirrorless", "gopro",
            "watch", "smartwatch", "band",
            "charger", "power bank", "cable", "hub", "router",
            "refrigerator", "washing machine", "microwave", "ac", "air conditioner",
            "wh-", "qc45", "xm5", "wf-", "wd-",  # model number patterns
        ],
        "retailers": [
            "amazon.in", "flipkart.com", "reliancedigital.in",
            "croma.com", "vijaysales.com", "tatacliq.com",
        ],
        "skip_retailers": ["myntra.com", "ajio.com", "nykaa.com", "purplle.com"],
    },

    "fashion": {
        "keywords": [
            "t-shirt", "shirt", "jeans", "pants", "kurta", "kurti", "saree",
            "dress", "top", "jacket", "blazer", "hoodie", "sweatshirt",
            "leggings", "skirt", "gown", "co-ord", "dupatta",
            "h&m", "zara", "gap", "uniqlo", "levis", "levi's",
            "tommy", "calvin klein", "forever 21",
        ],
        "retailers": [
            "myntra.com", "ajio.com", "flipkart.com", "meesho.com", "tatacliq.com",
        ],
        "skip_retailers": ["reliancedigital.in", "croma.com", "vijaysales.com", "nykaa.com"],
    },

    "shoes": {
        "keywords": [
            "shoes", "sneakers", "boots", "sandals", "heels", "slippers",
            "loafers", "moccasins", "flip flops", "footwear", "running shoes",
            "air max", "ultraboost", "stan smith",
        ],
        "retailers": [
            "myntra.com", "ajio.com", "flipkart.com", "amazon.in", "tatacliq.com",
        ],
        "skip_retailers": ["reliancedigital.in", "croma.com", "nykaa.com"],
    },

    "beauty": {
        "keywords": [
            "sunscreen", "serum", "moisturizer", "cream", "lotion", "spf",
            "toner", "face wash", "cleanser", "mask", "primer",
            "aha", "bha", "niacinamide", "vitamin c", "retinol", "hyaluronic",
            "shampoo", "conditioner", "hair oil", "hair mask", "hair serum",
            "lipstick", "lip gloss", "foundation", "concealer", "blush",
            "eyeshadow", "mascara", "eyeliner", "kajal", "makeup",
            # Fragrance — HIGH PRIORITY keywords (beats brand name matching)
            "perfume", "fragrance", "edp", "edt", "eau de parfum", "eau de toilette",
            "cologne", "attar", "oud", "deodorant", "deo", "body mist", "body spray",
            "mamaearth", "minimalist", "mcaffeine", "plum", "dot & key",
            "the ordinary", "cetaphil", "neutrogena", "lakme", "sugar",
            "fogg", "skinn", "engage", "denver", "axe",  # deo/fragrance brands
        ],
        # HIGH_PRIORITY: if these words appear, override any brand-based category
        "priority_keywords": [
            "edp", "edt", "eau de parfum", "eau de toilette", "perfume",
            "fragrance", "attar", "cologne", "serum", "sunscreen", "moisturizer",
        ],
        "retailers": [
            "nykaa.com", "amazon.in", "flipkart.com", "purplle.com", "myntra.com",
        ],
        "skip_retailers": ["reliancedigital.in", "croma.com", "vijaysales.com", "ajio.com"],
    },

    "sports": {
        "keywords": [
            "gym", "fitness", "yoga", "cycling", "swimming", "badminton",
            "cricket", "football", "tennis", "sports bag", "protein", "supplement",
        ],
        "retailers": [
            "amazon.in", "flipkart.com", "myntra.com", "ajio.com",
        ],
        "skip_retailers": ["reliancedigital.in", "croma.com", "nykaa.com"],
    },

    "jewellery": {
        "keywords": [
            "gold", "silver", "diamond", "ring", "necklace", "earring", "bracelet",
            "tanishq", "malabar", "helios", "titan",
        ],
        "retailers": [
            "amazon.in", "flipkart.com", "myntra.com", "tatacliq.com",
        ],
        "skip_retailers": ["reliancedigital.in", "nykaa.com"],
    },
}

# ── Brand → their official website mapping ───────────────────────────────────
BRAND_WEBSITES: dict[str, str] = {
    # Electronics
    "apple":      "apple.com",
    "samsung":    "samsung.com",
    "sony":       "sony.co.in",
    "lg":         "lg.com/in",
    "oneplus":    "oneplus.com/in",
    "realme":     "realme.com/in",
    "boat":       "boat-lifestyle.com",   # Shopify
    "boAt":       "boat-lifestyle.com",
    "noise":      "gonoise.com",
    "jbl":        "jbl.com/en-in",
    "bose":       "boseindia.com",
    "hp":         "hp.com/in",
    "dell":       "dell.com/en-in",
    "lenovo":     "lenovo.com/in",
    "asus":       "asus.com/in",
    # Fashion
    "h&m":        "hm.com",
    "zara":       "zara.com/in",
    "uniqlo":     "uniqlo.com/in",
    "nike":       "nike.com",
    "adidas":     "adidas.co.in",
    "puma":       "puma.com",
    "reebok":     "reebok.in",
    "skechers":   "skechers.com/en-in",
    "levi's":     "levi.com/en-in",
    "levis":      "levi.com/en-in",
    "gap":        "gap.com",
    "bewakoof":   "bewakoof.com",
    "the souled store": "thesouledstore.com",   # Shopify
    # Beauty
    "mamaearth":  "mamaearth.in",    # Shopify
    "minimalist": "minimalist.in",   # Shopify
    "mcaffeine":  "mcaffeine.com",   # Shopify
    "plum":       "plumgoodness.com",
    "dot & key":  "dotandkey.com",
    "forest essentials": "forestessentialsindia.com",
    # Watches/jewellery
    "tanishq":    "tanishq.co.in",
    "titan":      "titanworld.com",
    "fastrack":   "fastrack.in",
}


# ── Spec/Metadata extraction ──────────────────────────────────────────────────

class ProductSpec:
    """Structured metadata extracted from a product name/query."""

    def __init__(self):
        self.size:          Optional[str] = None   # S, M, L, XL / UK 8 / EU 42
        self.color:         Optional[str] = None   # Black, White, Red ...
        self.volume:        Optional[str] = None   # 30ml, 100ml, 500g ...
        self.concentration: Optional[str] = None   # 10%, 0.3%, 5% ...
        self.ram:           Optional[str] = None   # 8GB, 12GB (phones/laptops)
        self.storage:       Optional[str] = None   # 128GB, 256GB, 512GB
        self.variant:       Optional[str] = None   # WiFi, WiFi+Cellular, 4G, 5G
        self.size_type:     Optional[str] = None   # "clothing" | "shoe" | "liquid"

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def is_empty(self) -> bool:
        return all(v is None for v in self.__dict__.values())


def extract_specs(query: str) -> ProductSpec:
    """
    Extract product specifications/metadata from a search query.
    Used for:
      - UI filter chips (show size selector for fashion/shoes)
      - API variant-aware searching (add size to query when relevant)
      - Database metadata storage for accurate product matching

    Examples:
      "H&M Slim Fit T-Shirt Size L Navy Blue"
        → size="L", size_type="clothing", color="Navy Blue"

      "Minimalist Vitamin C Serum 10% 30ml"
        → volume="30ml", concentration="10%"

      "Samsung Galaxy S24 8GB 256GB Phantom Black"
        → ram="8GB", storage="256GB", color="Phantom Black"

      "Nike Air Max 270 UK 10 White"
        → size="UK 10", size_type="shoe", color="White"
    """
    spec  = ProductSpec()
    text  = query.lower()

    # ── Clothing size ─────────────────────────────────────────────────────────
    clothing_size = re.search(
        r'\bsize[:\s]+([xsml]{1,2}|[0-9]{1,2}-[0-9]{1,2})\b'
        r'|\b(xs|s|m|l|xl|xxl|xxxl|2xl|3xl)\b',
        text
    )
    if clothing_size:
        spec.size      = (clothing_size.group(1) or clothing_size.group(2) or "").upper()
        spec.size_type = "clothing"

    # ── Shoe size (UK/EU/US) ──────────────────────────────────────────────────
    shoe_size = re.search(
        r'\b(?:uk|us|eu|in)\s*([0-9]{1,2}(?:\.[05])?)\b'
        r'|\bsize\s+([0-9]{1,2})\b(?!gb|mb|ml|g\b)',
        text
    )
    if shoe_size and not spec.size:
        raw = shoe_size.group(0).strip()
        spec.size      = raw.upper()
        spec.size_type = "shoe"

    # ── Color ─────────────────────────────────────────────────────────────────
    COLORS = [
        "black", "white", "grey", "gray", "red", "blue", "navy", "green",
        "yellow", "orange", "pink", "purple", "brown", "beige", "ivory",
        "gold", "silver", "rose gold", "midnight", "starlight", "titanium",
        "phantom", "glacier", "graphite", "coral", "cream", "olive", "khaki",
    ]
    for color in COLORS:
        if re.search(rf'\b{re.escape(color)}\b', text):
            spec.color = color.title()
            break

    # ── Volume / Weight (beauty, household) ──────────────────────────────────
    vol = re.search(r'\b(\d+(?:\.\d+)?)\s*(ml|l|litre|liter|g|gm|gms|kg|oz)\b', text)
    if vol:
        spec.volume = f"{vol.group(1)}{vol.group(2).lower()}"

    # ── Concentration (serums, supplements) ──────────────────────────────────
    conc = re.search(r'\b(\d+(?:\.\d+)?)\s*%', text)
    if conc:
        spec.concentration = f"{conc.group(1)}%"

    # ── RAM (phones, laptops) ─────────────────────────────────────────────────
    ram = re.search(r'\b(\d+)\s*gb(?=\s+\d+\s*(?:gb|tb)|\s+ram|\b)', text)
    if ram:
        # First occurrence of GB pattern is usually RAM in "8GB 256GB" format
        spec.ram = f"{ram.group(1)}GB"

    # ── Storage (phones, laptops, tablets) ───────────────────────────────────
    storage = re.search(r'\b(\d+)\s*(tb|gb)\b(?!.*\d+\s*(?:gb|tb)\s+ram)', text)
    # Take last GB match as storage (not RAM which is usually first)
    all_gb = re.findall(r'(\d+)\s*gb', text)
    if len(all_gb) >= 2:
        spec.storage = f"{all_gb[-1]}GB"
    elif storage:
        unit = storage.group(2).upper()
        spec.storage = f"{storage.group(1)}{unit}"

    # ── Variant (connectivity, generation) ───────────────────────────────────
    variant = re.search(
        r'\b(wifi\s*\+\s*cellular|wi-fi\s*only|4g|5g|lte|wifi only|bluetooth|wired|wireless)\b',
        text
    )
    if variant:
        spec.variant = variant.group(1).title()

    return spec


# ── Category detection ────────────────────────────────────────────────────────

def detect_category(query: str) -> Optional[str]:
    """
    Detect product category from query text.

    Priority system:
      Step 1 — Check PRIORITY keywords first (product-type beats brand name)
               "H&M EDP" → 'edp' is a beauty priority keyword → category=beauty
               Even though 'h&m' is also a fashion keyword.

      Step 2 — Score all categories by keyword count
               Most matches wins.

    Returns: "electronics" | "fashion" | "shoes" | "beauty" | "sports" | "jewellery" | None
    """
    q = query.lower()

    # Step 1: Priority keyword override — product type beats brand name
    for category, config in CATEGORIES.items():
        priority_kws = config.get("priority_keywords", [])
        if any(kw in q for kw in priority_kws):
            return category   # product type is definitive — return immediately

    # Step 2: Normal keyword scoring
    best_category = None
    best_score    = 0
    for category, config in CATEGORIES.items():
        score = sum(1 for kw in config["keywords"] if kw in q)
        if score > best_score:
            best_score    = score
            best_category = category

    return best_category if best_score > 0 else None


def get_relevant_retailers(query: str, all_profiles: list) -> tuple[list, list[str]]:
    """
    Filter retailer profiles to only those relevant for the detected category.
    Also returns brand website URLs to include in search.

    Returns: (filtered_profiles, brand_website_urls)

    Example:
      query = "H&M Slim Fit Shirt Size L"
      → category: "fashion"
      → profiles: [myntra, ajio, flipkart, meesho]  (NO amazon, reliancedigital)
      → brand_urls: ["https://www.hm.com"]
    """
    category = detect_category(query)
    q        = query.lower()

    # ── Filter profiles by category ───────────────────────────────────────────
    if category and category in CATEGORIES:
        skip    = set(CATEGORIES[category].get("skip_retailers", []))
        allowed = set(CATEGORIES[category].get("retailers", []))
        filtered = [
            p for p in all_profiles
            if p.domain not in skip and (not allowed or p.domain in allowed)
        ]
    else:
        filtered = all_profiles  # unknown category = search everywhere

    # ── Detect brand website ──────────────────────────────────────────────────
    brand_urls = []
    for brand, domain in BRAND_WEBSITES.items():
        if brand.lower() in q:
            brand_urls.append(f"https://www.{domain}")
            break  # one brand per query

    return filtered, brand_urls


def build_variant_query(base_query: str, spec: ProductSpec) -> str:
    """
    Build a more specific search query by appending key specs.
    Helps retailer search engines show the right variant.

    "H&M Shirt" + size="L", color="Blue"
    → "H&M Shirt L Blue"

    "Samsung Galaxy S24" + ram="8GB", storage="256GB"
    → "Samsung Galaxy S24 8GB 256GB"
    """
    parts = [base_query]
    if spec.ram:     parts.append(spec.ram)
    if spec.storage: parts.append(spec.storage)
    if spec.volume:  parts.append(spec.volume)
    return " ".join(parts)
