"""
Site Profiles — per-domain scraping + search strategy registry.
The universal scraper uses this to:
  1. Scrape any product URL (right HTTP method + CSS selectors)
  2. Search for products by text (search URL/API + result parsing)

Adding a new retailer to text search = add 15 lines here. Zero new Python files.

Search types:
  "html"          — fetch search results HTML, parse CSS selector cards (Amazon)
  "json_api"      — call JSON REST API endpoint (Reliance, Nykaa, Ajio)
  "embedded_json" — fetch HTML page, extract JSON embedded in <script> (Myntra, Flipkart)

Fetch tiers:
  TIER_1_URLLIB     — plain urllib (fastest, no deps)
  TIER_2_CURL_CFFI  — Chrome TLS fingerprint (Cloudflare bypass)
  TIER_3_HTTPX      — HTTP/2 (modern sites)
  TIER_4_PLAYWRIGHT — full JS execution (heavy sites)
  TIER_SHOPIFY      — Shopify /products/handle.json API
  TIER_WOOCOMMERCE  — WooCommerce REST API
"""

from dataclasses import dataclass, field
from typing import Optional

# ── Fetch tier constants ─────────────────────────────────────────────────────
TIER_1_URLLIB     = "urllib"
TIER_2_CURL_CFFI  = "curl_cffi"
TIER_3_HTTPX      = "httpx"
TIER_4_PLAYWRIGHT = "playwright"
TIER_SHOPIFY      = "shopify"
TIER_WOOCOMMERCE  = "woocommerce"


@dataclass
class SiteProfile:
    """
    Complete configuration for scraping + searching a website.
    Used by universal.py for both URL scraping and text search.
    """
    domain: str
    tier:   str                    # best HTTP method for this site

    # ── URL scraping: CSS selectors ──────────────────────────────────────────
    price_selectors: list[str] = field(default_factory=list)
    mrp_selectors:   list[str] = field(default_factory=list)
    member_price_selectors:   list[str] = field(default_factory=list)  # Prime/Member prices
    login_required_selectors: list[str] = field(default_factory=list)  # "Login to see price"
    name_selectors:  list[str] = field(default_factory=list)
    image_selectors: list[str] = field(default_factory=list)
    stock_selectors: list[str] = field(default_factory=list)
    wait_selector:   Optional[str] = None  # Playwright: wait for this before parsing
    referrer:        Optional[str] = None  # Referer header (some sites require it)

    # ── Text search: how to search this site ─────────────────────────────────
    # search_url    → use for HTML search result pages   e.g. "https://amazon.in/s?k={query}"
    # search_api_url → use for JSON API endpoints        e.g. "https://api.reliance.in/search?q={query}"
    # Put {query} exactly where the search term goes.
    search_url:     Optional[str] = None
    search_api_url: Optional[str] = None

    # How to parse the search response
    search_type:    str = "html"   # "html" | "json_api" | "embedded_json"

    # ── HTML result card parsing (search_type = "html") ──────────────────────
    result_container_sel: Optional[str] = None   # selector for each product card
    result_name_sel:      Optional[str] = None
    result_price_sel:     Optional[str] = None
    result_mrp_sel:       Optional[str] = None
    result_link_sel:      Optional[str] = None   # anchor tag inside each card
    result_image_sel:     Optional[str] = None
    result_link_prefix:   str = ""               # prepend base URL to relative hrefs

    # ── JSON API result parsing (search_type = "json_api") ───────────────────
    # Dot-separated path to products array: "products" or "response.products"
    json_products_path: str = "products"
    json_name_key:      str = "name"
    json_price_key:     str = "price"       # may be nested: "price.selling"
    json_mrp_key:       str = "mrp"
    json_url_key:       str = "url"
    json_image_key:     str = "image"
    json_brand_key:     str = "brand"
    json_url_prefix:    str = ""            # prepend base URL if relative

    # ── Embedded JSON extraction (search_type = "embedded_json") ─────────────
    # Regex pattern to find the JSON block in page HTML.
    # Must have one capture group that returns valid JSON.
    embedded_json_pattern: Optional[str] = None

    notes: str = ""


# ── Domain → SiteProfile registry ───────────────────────────────────────────
SITE_PROFILES: dict[str, SiteProfile] = {

    # ══════════════════════════════════════════════════════════════════════════
    # MAJOR INDIAN RETAILERS (text search + URL scraping)
    # ══════════════════════════════════════════════════════════════════════════

    "amazon.in": SiteProfile(
        domain="amazon.in", tier=TIER_1_URLLIB,

        # URL scraping
        price_selectors=[
            "#corePrice_feature_div .a-price-whole",
            ".apexPriceToPay .a-price-whole",
            "#priceblock_ourprice",
            ".a-price-whole",
            "[itemprop='price']",
        ],
        member_price_selectors=[
            ".apexPriceToPay .a-offscreen",
            "#corePrice_feature_div .a-offscreen",
            ".prime-exclusive-price"
        ],
        login_required_selectors=[
            "#primeExclusivePricingMessage",
            ".login-to-see-price"
        ],
        mrp_selectors=[".a-price.a-text-price .a-offscreen", "#priceblock_saleprice"],
        name_selectors=["#productTitle", "h1[itemprop='name']"],
        image_selectors=["#landingImage", "#imgBlkFront"],

        # Text search (HTML card parsing)
        search_url="https://www.amazon.in/s?k={query}&ref=nb_sb_noss",
        search_type="html",
        result_container_sel="div[data-component-type='s-search-result']",
        result_name_sel="h2 span",
        result_price_sel="span.a-price-whole",
        result_mrp_sel="span.a-text-price .a-offscreen",
        result_link_sel="a.a-link-normal[href]",
        result_image_sel="img.s-image",
        result_link_prefix="https://www.amazon.in",
        notes="No Cloudflare. urllib works. JSON-LD available on product pages.",
    ),

    "flipkart.com": SiteProfile(
        domain="flipkart.com", tier=TIER_2_CURL_CFFI,

        # URL scraping
        price_selectors=["div[class*='_30jeq3']", "._16Jk6d", "[class*='price'][class*='offer']"],
        mrp_selectors=["div[class*='_3I9_wc']", "[class*='price'][class*='cross']"],
        name_selectors=["h1.yhB1nd span", "h1[class*='title']"],
        image_selectors=["img._396cs4", "img[class*='product']"],

        # Text search (embedded JSON in HTML)
        search_url="https://www.flipkart.com/search?q={query}&marketplace=FLIPKART",
        search_type="embedded_json",
        # Flipkart embeds product data as JSON in window.__INITIAL_STATE__
        embedded_json_pattern=r'window\.__INITIAL_STATE__\s*=\s*(\{.*?"pageData".*?\});',
        # Fallback HTML parsing if JSON not found
        result_container_sel="div[data-id]",
        result_name_sel="a[class*='s1Q9rs'], ._4rR01T, ._2WkVRV",
        result_price_sel="div[class*='_30jeq3']",
        result_mrp_sel="div[class*='_3I9_wc']",
        result_link_sel="a[href][class*='s1Q9rs'], a._1fQZEK, a._2UzuFa",
        result_image_sel="img[class*='_396cs4']",
        result_link_prefix="https://www.flipkart.com",
        notes="Cloudflare — curl_cffi mandatory.",
    ),

    "myntra.com": SiteProfile(
        domain="myntra.com", tier=TIER_1_URLLIB,

        # URL scraping
        price_selectors=["[class*='pdp-price'] strong", ".pdp-price", "span.pdp-price"],
        mrp_selectors=["[class*='pdp-mrp'] s", ".original-price", "span.pdp-mrp"],
        name_selectors=["h1.pdp-title", "h1.pdp-name", "h1"],
        image_selectors=["[class*='image-grid-image'] img", ".image-grid img", "img.pdp-main-img"],

        # Text search (embedded JSON via regex)
        search_url="https://www.myntra.com/search?q={query}",
        search_type="embedded_json",
        embedded_json_pattern=r'"productId"\s*:\s*(\d+)',   # triggers custom parser in universal.py
        notes="No Cloudflare. Prices in embedded JS (regex extraction).",
    ),

    "reliancedigital.in": SiteProfile(
        domain="reliancedigital.in", tier=TIER_1_URLLIB,

        # URL scraping
        price_selectors=["[class*='selling-price']", ".pdp__price", "[itemprop='price']"],
        mrp_selectors=["[class*='mrp']", ".pdp__mrp"],
        name_selectors=["h1.pdp__title", "h1[itemprop='name']"],
        image_selectors=[".pdp__image img", "[itemprop='image']"],

        # Text search (JSON API)
        search_api_url=(
            "https://www.reliancedigital.in/rildigitalws/v2/rrldigital/products/search"
            "?query={query}&pageNumber=0&pageSize=10&sort=relevance"
        ),
        search_type="json_api",
        json_products_path="products",
        json_name_key="name",
        json_price_key="price.selling",
        json_mrp_key="price.mrp",
        json_url_key="slug",
        json_image_key="images.0.url",
        json_brand_key="brand",
        json_url_prefix="https://www.reliancedigital.in/",
        notes="No CF. Has proper REST API.",
    ),

    "nykaa.com": SiteProfile(
        domain="nykaa.com", tier=TIER_2_CURL_CFFI,

        # URL scraping
        price_selectors=["[class*='offer-price']", "[class*='selling-price']", "[itemprop='price']"],
        mrp_selectors=["[class*='mrp']", "[class*='base-price']"],
        name_selectors=["h1[class*='product-name']", "h1"],
        image_selectors=["[class*='product-image'] img"],

        # Text search (JSON API)
        search_api_url=(
            "https://www.nykaa.com/api/2.0/page/search"
            "?query={query}&page=1&itemsPerPage=10"
        ),
        search_type="json_api",
        json_products_path="response.products",
        json_name_key="name",
        json_price_key="discountedPrice",
        json_mrp_key="mrp",
        json_url_key="slug",
        json_image_key="imageUrl",
        json_url_prefix="https://www.nykaa.com/",
        notes="Light CF — curl_cffi handles it.",
    ),

    "ajio.com": SiteProfile(
        domain="ajio.com", tier=TIER_3_HTTPX,

        # URL scraping
        price_selectors=["[class*='price'][class*='bold']", ".price", "span.pdp-price"],
        mrp_selectors=["[class*='price'][class*='strike']", ".original-price"],
        name_selectors=["h1[class*='name']", "h1"],
        image_selectors=["[class*='image'] img", "img.pdp-main-img"],

        # Text search (JSON API)
        search_api_url=(
            "https://www.ajio.com/api/search"
            "?query={query}&currentPage=0&pageSize=20&format=json&sortby=relevance&lang=en_IN&curr=INR"
        ),
        search_type="json_api",
        json_products_path="products",
        json_name_key="name",
        json_price_key="price.value",
        json_mrp_key="price.mrp",
        json_url_key="url",
        json_image_key="thumbnail",
        json_brand_key="brandName",
        json_url_prefix="https://www.ajio.com",
        notes="HTTP/2 site — httpx first.",
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # ELECTRONICS (URL scraping only — no text search yet)
    # ══════════════════════════════════════════════════════════════════════════

    "croma.com": SiteProfile(
        domain="croma.com", tier=TIER_1_URLLIB,
        price_selectors=["[class*='amount'][class*='offer']", ".pdp-selling-price", "[itemprop='price']"],
        mrp_selectors=["[class*='amount'][class*='regular']", ".pdp-mrp"],
        name_selectors=["h1.pdp-product-name", "h1[itemprop='name']"],
        image_selectors=[".pdp-image img", "[itemprop='image']"],

        # Text search (HTML card)
        search_url="https://www.croma.com/searchB?q={query}%3Arelevance&text={query}",
        search_type="html",
        result_container_sel="li.product__list--item",
        result_name_sel="h3.product__list--name",
        result_price_sel="span.amount",
        result_link_sel="a.product__list--anchor",
        result_image_sel="img.product__list--arrowimg",
        result_link_prefix="https://www.croma.com",
        notes="No bot protection. Search now supported.",
    ),

    "cashify.in": SiteProfile(
        domain="cashify.in", tier=TIER_1_URLLIB,
        price_selectors=[
            "[class*='selling-price']", "[class*='offer-price']",
            ".price", "[itemprop='price']",
        ],
        mrp_selectors=["[class*='mrp']", "[class*='original-price']"],
        name_selectors=["h1[class*='product-name']", "h1[class*='title']", "h1"],
        image_selectors=["[class*='product-image'] img", ".pdp-image img"],

        # Text search (HTML)
        search_url="https://www.cashify.in/search?q={query}",
        search_type="html",
        result_container_sel="div.product-card, div[class*='ProductCard']",
        result_name_sel="h3, [class*='product-name'], [class*='title']",
        result_price_sel="[class*='price'], span.amount",
        result_link_sel="a[href]",
        result_image_sel="img",
        result_link_prefix="https://www.cashify.in",
        notes="Refurbished electronics. No heavy bot protection.",
    ),

    "vijaysales.com": SiteProfile(
        domain="vijaysales.com", tier=TIER_2_CURL_CFFI,
        price_selectors=["[class*='offer-price']", ".special-price", "[itemprop='price']"],
        mrp_selectors=["[class*='regular-price']", ".old-price"],
        name_selectors=["h1.product-name", "h1[itemprop='name']"],
        image_selectors=[".product-img img", "[itemprop='image']"],
    ),

    "tatacliq.com": SiteProfile(
        domain="tatacliq.com", tier=TIER_2_CURL_CFFI,
        price_selectors=["[class*='DiscountedPrice']", "[itemprop='price']", ".ProductDescription__price"],
        mrp_selectors=["[class*='MRPPrice']", ".ProductDescription__mrp"],
        name_selectors=["[class*='ProductName']", "h1"],
        image_selectors=["[class*='ProductImage'] img", ".ProductVisuals__image"],
        
        # Text search (HTML card)
        search_url="https://www.tatacliq.com/search/?text={query}",
        search_type="html",
        result_container_sel="div.ProductModule__base",
        result_name_sel="div.ProductDescription__content h2",
        result_price_sel="div.ProductDescription__price h3",
        result_mrp_sel="div.ProductDescription__mrp h4",
        result_link_sel="a",
        result_link_prefix="https://www.tatacliq.com",
    ),

    "samsung.com": SiteProfile(
        domain="samsung.com", tier=TIER_1_URLLIB,
        price_selectors=["[class*='price'][class*='txt']", "[data-gtm-price]"],
        mrp_selectors=["[class*='price'][class*='origin']"],
        name_selectors=["h1.visual-title", "h1.product-name"],
        image_selectors=[".pdp-visual img"],
    ),

    "apple.com": SiteProfile(
        domain="apple.com", tier=TIER_1_URLLIB,
        price_selectors=["[class*='current_price']", "[data-autom='price']"],
        name_selectors=["h1[data-autom='product-name']", "h1"],
        image_selectors=[".overview-hero-image img"],
        notes="Heavy JSON-LD — extract_jsonld_price() is primary.",
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # SHOPIFY D2C BRANDS
    # ══════════════════════════════════════════════════════════════════════════

    "boat-lifestyle.com": SiteProfile(
        domain="boat-lifestyle.com", tier=TIER_SHOPIFY,
        notes="Shopify. /products/handle.json API.",
    ),
    "mamaearth.in":   SiteProfile(domain="mamaearth.in",   tier=TIER_SHOPIFY),
    "minimalist.in":  SiteProfile(domain="minimalist.in",  tier=TIER_SHOPIFY),
    "mcaffeine.com":  SiteProfile(domain="mcaffeine.com",  tier=TIER_SHOPIFY),
    "thesouledstore.com": SiteProfile(domain="thesouledstore.com", tier=TIER_SHOPIFY),

    # ══════════════════════════════════════════════════════════════════════════
    # FASHION — URL scraping only
    # ══════════════════════════════════════════════════════════════════════════

    "bewakoof.com": SiteProfile(
        domain="bewakoof.com", tier=TIER_2_CURL_CFFI,
        price_selectors=["[class*='discounted-price']", "[class*='selling-price']"],
        mrp_selectors=["[class*='mrp']"],
        name_selectors=["h1[class*='product-name']", "h1"],
        image_selectors=["[class*='product-image'] img"],
    ),

    "lenskart.com": SiteProfile(
        domain="lenskart.com", tier=TIER_2_CURL_CFFI,
        price_selectors=["[class*='price'][class*='final']", ".pdp-price"],
        mrp_selectors=["[class*='price'][class*='mark']"],
        name_selectors=["h1[class*='product-name']", "h1"],
        image_selectors=[".pdp-image img"],
    ),

    "tanishq.co.in": SiteProfile(
        domain="tanishq.co.in", tier=TIER_4_PLAYWRIGHT,
        price_selectors=["[class*='price'][class*='final']", ".product-price"],
        name_selectors=["h1.product-name", "h1"],
        image_selectors=[".product-gallery img"],
        wait_selector=".product-price",
    ),

    "meesho.com": SiteProfile(
        domain="meesho.com", tier=TIER_4_PLAYWRIGHT,
        price_selectors=["[class*='price']", "h4[class*='Text']"],
        name_selectors=["h1[class*='Text']", "h1"],
        image_selectors=["[class*='image'] img"],
        wait_selector="h1",
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # BEAUTY / HEALTH — URL scraping only
    # ══════════════════════════════════════════════════════════════════════════

    "purplle.com": SiteProfile(
        domain="purplle.com", tier=TIER_1_URLLIB,
        price_selectors=["[class*='selling-price']", "[itemprop='price']"],
        mrp_selectors=["[class*='mrp']"],
        name_selectors=["h1[class*='product-name']", "h1"],
        image_selectors=[".product-image img"],
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # GLOBAL BRANDS — URL scraping only
    # ══════════════════════════════════════════════════════════════════════════

    "nike.com": SiteProfile(
        domain="nike.com", tier=TIER_2_CURL_CFFI,
        price_selectors=["[data-testid='currentPrice-container']", "[itemprop='price']"],
        mrp_selectors=["[data-testid='initialPrice-container']"],
        name_selectors=["h1[data-testid='product-title']", "h1"],
        image_selectors=["[data-testid='product-hero'] img"],
    ),

    "adidas.co.in": SiteProfile(
        domain="adidas.co.in", tier=TIER_2_CURL_CFFI,
        price_selectors=["[data-auto-id='product-price']", "[itemprop='price']", ".gl-price-item"],
        name_selectors=["h1[data-auto-id='product-title']", "h1"],
        image_selectors=[".gl-lookahead-image img", ".product-image img"],
        
        # Text search (HTML)
        search_url="https://www.adidas.co.in/search?q={query}",
        search_type="html",
        result_container_sel="div.glass-product-card",
        result_name_sel="p.glass-product-card__title",
        result_price_sel="div.gl-price-item",
        result_link_sel="a.glass-product-card__assets-link",
        result_image_sel="img.glass-product-card__image",
        result_link_prefix="https://www.adidas.co.in",
    ),

    "shoppersstop.com": SiteProfile(
        domain="shoppersstop.com", tier=TIER_2_CURL_CFFI,
        price_selectors=[".pdp-price", "[itemprop='price']"],
        mrp_selectors=[".pdp-mrp"],
        name_selectors=[".pdp-name", "h1"],
        image_selectors=[".pdp-image img"],
        search_url="https://www.shoppersstop.com/search/?text={query}",
        search_type="html",
        result_container_sel="li.product-item",
        result_name_sel="div.pro-name a",
        result_price_sel="span.pro-price",
        result_link_sel="div.pro-list-img a",
        result_link_prefix="https://www.shoppersstop.com",
    ),

    "puma.com": SiteProfile(
        domain="puma.com", tier=TIER_1_URLLIB,
        price_selectors=["[itemprop='price']", ".product-prices__price"],
        name_selectors=["h1[class*='product-name']", "h1"],
        image_selectors=[".product-image img"],
    ),
}


# ── Lookup helpers ────────────────────────────────────────────────────────────

def get_profile(url: str) -> Optional[SiteProfile]:
    """Return the SiteProfile for a given URL or domain, or None if unknown."""
    from urllib.parse import urlparse
    raw = (url or "").strip().lower()
    parsed = urlparse(raw)
    domain = (parsed.netloc or parsed.path).lower().replace("www.", "").strip("/")
    for registered, profile in SITE_PROFILES.items():
        if domain.endswith(registered):
            return profile
    return None


def get_searchable_profiles() -> list[SiteProfile]:
    """Return all profiles that support text search."""
    return [
        p for p in SITE_PROFILES.values()
        if p.search_url or p.search_api_url
    ]


def detect_platform(html: str) -> Optional[str]:
    """Detect Shopify or WooCommerce from HTML fingerprint."""
    if not html:
        return None
    h = html[:5000]
    if "Shopify.theme" in h or "cdn.shopify.com" in h or "shopify.com/s/files" in h:
        return TIER_SHOPIFY
    if "woocommerce" in h.lower() or "wc-add-to-cart" in h:
        return TIER_WOOCOMMERCE
    return None


def resolve_json_path(data: dict, path: str):
    """
    Resolve dot-separated JSON path. Supports array index notation.
    e.g. "price.selling" → data["price"]["selling"]
         "images.0.url"  → data["images"][0]["url"]
    Returns None if path not found.
    """
    parts = path.split(".")
    current = data
    for part in parts:
        if current is None:
            return None
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
