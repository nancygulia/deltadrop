"""
DeltaDrop AI Price Intelligence — powered by Google Gemini.
Provides ShopSavvy-style buy/wait recommendations grounded in live product data.
"""
import logging
from datetime import datetime, timezone
import json

<<<<<<< HEAD
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import selectinload
=======
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3

from app.core.security import get_current_user
from app.models.user import User
from app.core.config import settings

router = APIRouter(prefix="/ai", tags=["AI Intelligence"])
logger = logging.getLogger(__name__)

<<<<<<< HEAD
# Rate limiter
from app.core.rate_limit import rate_limiter

# ── Input size limits ─────────────────────────────────────────────────────────
MAX_PRODUCT_NAME_LEN   = 200
MAX_QUESTION_LEN       = 500
MAX_CONTEXT_LEN        = 5000
MAX_PRICE_HISTORY_LEN  = 500
MAX_CATEGORY_LEN       = 100
MAX_TEXT_FIELD_LEN      = 1000

=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are DeltaDrop's Price Intelligence Engine — a razor-sharp analyst for the Indian e-commerce market.

Your role is identical to ShopSavvy's deal-scoring engine, but tuned specifically for Indian retail:
- You process real, live scraped pricing data from Amazon.in, Flipkart, Myntra, Reliance Digital, Nykaa, Croma, and Tata CLiQ
- You deliver concise, confident, data-backed buy/wait recommendations — never vague or hedging
- You think like a precision trader: every rupee saved is a confirmed alpha signal

## Your Intelligence Framework

### Signal Hierarchy (in order of weight)
1. **Price vs All-Time Low** — If current price is within 5% of ATL, it's a BUY_NOW signal regardless of other factors
2. **30-Day Trend** — Consistent downtrend means WAIT; flat or uptrend means BUY_NOW before the reversal
3. **Multi-Retailer Spread** — If best price is 8%+ below second-best, arbitrage window is closing fast → BUY_NOW
4. **Seasonality** — Festive season (Oct-Nov), Republic Day (Jan), Independence Day (Aug), End-of-Season (Jan & Jun/Jul) are historically the lowest points for Indian retail
5. **Discount from MRP** — Under 10%: weak deal. 20-30%: good. 30%+: strong buy signal. 50%+: clearance, act immediately

### Verdict Rules
- **BUY NOW** → Issue the signal when ≥2 bullish signals align. Be decisive.
- **WAIT** → Issue when a price drop of 10%+ is statistically likely in the next 2-4 weeks
- **NEUTRAL** → Use sparingly, only when signals are genuinely mixed with no clear edge

### Output Format
Always respond in exactly this structure:

**VERDICT: [BUY NOW / WAIT / NEUTRAL]**

**Signal:** [One sharp sentence explaining the primary data signal]

**Analysis:** [2-3 sentences max. Reference specific numbers from the data provided. Name the cheapest retailer. Mention the all-time low if relevant.]

**Action:** [One specific, time-bound action the user should take right now]

---

## Rules
- Always reference rupee amounts using ₹ symbol
- Always name the specific retailer with the best price
- Never say "it depends" — commit to a verdict with reasoning
- If the user asks a general question not related to the product data, answer it but pivot back to the product's price signal
- Keep total response under 180 words — precision over verbosity
- If data shows a product near its all-time low AND listed on multiple retailers within 2% of each other, this is a FLOOR SIGNAL — always recommend BUY NOW
"""


# ── Schemas ───────────────────────────────────────────────────────────────────

class AIRequest(BaseModel):
<<<<<<< HEAD
    product_context: str = Field(..., max_length=MAX_CONTEXT_LEN)
    question:        str = Field(..., max_length=MAX_QUESTION_LEN)
=======
    product_context: str    # Structured product + price data block
    question:        str    # User's free-text question
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3


class AIResponse(BaseModel):
    answer:    str
    timestamp: str


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/ask", response_model=AIResponse)
async def ask_ai(
    req: AIRequest,
<<<<<<< HEAD
    request: Request,
=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    current_user: User = Depends(get_current_user),
):
    """
    AI price intelligence endpoint.
    Accepts structured product context + user question.
    Returns a ShopSavvy-style buy/wait recommendation grounded in real data.
    HARDENED: Never returns 500 — falls back to rule-based analysis if API unavailable.
    """
<<<<<<< HEAD
    # Rate limit: 20 AI requests per minute per IP
    rate_limiter.check(request, "ai-ask", max_requests=20, window_seconds=60)

=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if len(req.question) > 500:
        raise HTTPException(status_code=400, detail="Question too long (max 500 chars)")

    # ── Try Gemini AI (primary) ──────────────────────────────────────────
    try:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured")

        from google import genai
        client = genai.Client(api_key=api_key)

        # Gemini uses a single text prompt for simple chat structures
        full_prompt = f"{SYSTEM_PROMPT}\n\n[CONTEXT]\n{req.product_context}\n\n[USER QUESTION]\n{req.question}"
        
        import asyncio
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=full_prompt
        )
        
        answer = response.text
        logger.info(f"[AI] User {current_user.id} asked — {len(answer)} chars returned via Gemini")

        return AIResponse(
            answer    = answer,
            timestamp = datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.warning(f"[AI] Gemini issue ({e}) — using rule-based fallback")

    # ── Rule-based fallback (runs when AI is unavailable) ────────────────
    # Parse context for key signals to give an intelligent local answer
    ctx = req.product_context.lower()
    q   = req.question.lower()

    # Extract signals from context text
    near_atl  = "above all-time low" in ctx and any(c.isdigit() for c in ctx)
    trending_down = "dropping" in ctx or "downtrend" in ctx
    big_discount  = any(f"{d}%" in ctx for d in range(30, 100))
    in_stock      = "in stock" in ctx

    if near_atl or big_discount:
        verdict   = "BUY NOW"
        signal    = "Price is near historical lows with a significant discount from MRP."
        analysis  = "Based on the pricing data available, this appears to be a strong buying opportunity. The current price represents good value relative to the MRP and historical range."
        action    = "Buy now from the lowest-priced retailer shown in the comparison table."
    elif trending_down:
        verdict   = "WAIT"
        signal    = "Price trend is currently declining — a lower price may be available soon."
        analysis  = "The 30-day pricing trend indicates downward movement. Waiting 1-2 weeks may yield a better deal. Set a price alert at your target price to be notified automatically."
        action    = "Set a price alert below the current price and check back in 7-10 days."
    else:
        verdict   = "NEUTRAL"
        signal    = "Price is stable with no strong buy or wait signal at this time."
        analysis  = "Current pricing is within the normal range for this product. No imminent price drop is indicated, but no urgency to buy immediately either."
        action    = "Monitor via a DeltaDrop price alert set 5-10% below current price."

    fallback_answer = (
        f"**VERDICT: {verdict}**\n\n"
        f"**Signal:** {signal}\n\n"
        f"**Analysis:** {analysis}\n\n"
        f"**Action:** {action}\n\n"
        f"---\n"
        f"*Note: AI Sentinel operating in offline mode — running rule-based analysis. "
        f"Configure GEMINI_API_KEY for full Gemini-powered intelligence.*"
    )

    return AIResponse(
        answer    = fallback_answer,
        timestamp = datetime.now(timezone.utc).isoformat(),
    )



<<<<<<< HEAD
@router.get("/recommendation")
async def get_recommendation(
    product_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    Get AI price recommendation for a product.
    This endpoint combines ML prediction with AI analysis.
    """
    from app.models.product import Product, PriceHistory, PricePrediction
    from sqlalchemy import select
    from app.db.session import get_db
    from app.ml.predictor import run_prediction_for_product
    
    async with get_db().__anext__() as db:
        # Get product details
        result = await db.execute(
            select(Product).options(
                selectinload(Product.retailer_listings),
                selectinload(Product.predictions)
            ).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get latest prediction or create one
        prediction = None
        if product.predictions:
            latest = max(product.predictions, key=lambda p: p.predicted_at)
            prediction = {
                "predicted_price": float(latest.predicted_price),
                "predicted_low":   float(latest.predicted_low)   if latest.predicted_low  else None,
                "predicted_high":  float(latest.predicted_high)  if latest.predicted_high else None,
                "confidence":      float(latest.confidence)       if latest.confidence     else None,
                "horizon_days":    latest.horizon_days,
                "verdict":         latest.verdict,
                "reasoning":       latest.reasoning,
                "model_version":   latest.model_version,
                "predicted_at":    latest.predicted_at.isoformat(),
            }
        else:
            # Trigger prediction if none exists
            try:
                pred_result = await run_prediction_for_product(product_id, db)
                if pred_result:
                    prediction = pred_result
            except Exception as e:
                logger.warning(f"[AI] Failed to generate prediction: {e}")
        
        # Get current best price
        listings = [l for l in (product.retailer_listings or []) if l.is_active and l.current_price is not None]
        current_price = min([l.current_price for l in listings]) if listings else None
        
        # Build recommendation response
        if prediction:
            return {
                "verdict": prediction.get("verdict", "NEUTRAL"),
                "confidence": prediction.get("confidence"),
                "reasoning": prediction.get("reasoning"),
                "method": "ai_recommendation",
                "predicted_price": prediction.get("predicted_price"),
                "horizon_days": prediction.get("horizon_days"),
                "insights": {
                    "price_comparison": f"Current: ₹{current_price:,.0f} | Predicted: ₹{prediction.get('predicted_price', 0):,.0f}",
                    "trend_analysis": f"Confidence: {prediction.get('confidence', 0):.1%} | Horizon: {prediction.get('horizon_days', 14)} days",
                    "smart_recommendation": f"{prediction.get('verdict', 'WAIT')} around ₹{prediction.get('predicted_price', 0):,.0f}",
                    "suggested_alert_price": prediction.get("predicted_price", current_price),
                }
            }
        else:
            # Fallback recommendation
            return {
                "verdict": "NEUTRAL",
                "confidence": None,
                "reasoning": "AI analysis is being initialized. Please check back in a moment.",
                "method": "fallback_recommendation",
                "insights": {
                    "price_comparison": f"Current: ₹{current_price:,.0f}",
                    "trend_analysis": "Collecting market data...",
                    "smart_recommendation": "Monitor for price changes",
                    "suggested_alert_price": current_price,
                }
            }


=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
@router.get("/status")
async def ai_status(current_user: User = Depends(get_current_user)):
    """Check if the AI service is configured and reachable."""
    key_set = bool(settings.GEMINI_API_KEY)
    return {
        "available":    key_set,
        "model":        "gemini-2.5-flash",
        "status":       "ready" if key_set else "missing_api_key",
    }
<<<<<<< HEAD


# ── POST /api/v1/ai/analyze — Structured BUY/WAIT Analysis ──────────────────

class AnalyzeRequest(BaseModel):
    product_name: str
    price: float
    min_price: float
    max_price: float

class AnalyzeResponse(BaseModel):
    verdict: str
    message: str
    suggested_price: float

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_price(req: AnalyzeRequest, request: Request):
    """
    Secure AI analysis endpoint — accepts product pricing
    and returns a structured BUY/WAIT/CONSIDER decision with reasoning.
    """
    rate_limiter.check(request, "ai-analyze", max_requests=20, window_seconds=60)

    if req.price <= 0 or req.min_price <= 0 or req.max_price <= 0:
        raise HTTPException(status_code=400, detail="Prices must be positive")

    # ── Try Gemini ────────────────────────────────────────────────────────
    api_key = settings.GEMINI_API_KEY
    if api_key:
        try:
            from google import genai
            import asyncio as _asyncio

            client = genai.Client(api_key=api_key)

            prompt = f"""Analyze if current price is good or not for buying for {req.product_name}.
Current Price: ₹{req.price:,.0f}
Lowest Recorded: ₹{req.min_price:,.0f}
Highest Recorded: ₹{req.max_price:,.0f}

Return ONLY valid JSON, no markdown:
{{
  "verdict": "BUY" or "WAIT" or "CONSIDER",
  "message": "<1-2 sentence explanation referencing specific numbers>",
  "suggested_price": <integer — the price at which user should buy>
}}"""

            response = await _asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
            )
            text = (response.text or "").strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            parsed = json.loads(text.strip())
            verdict = str(parsed.get("verdict", "WAIT")).upper()
            if verdict not in ("BUY", "WAIT", "CONSIDER"):
                verdict = "WAIT"

            return AnalyzeResponse(
                verdict=verdict,
                message=parsed.get("message", "AI analysis complete."),
                suggested_price=float(parsed.get("suggested_price", req.min_price)),
            )

        except Exception as e:
            logger.warning(f"[AI/analyze] Gemini failed ({e}), using fallback")

    # ── Deterministic fallback ────────────────────────────────────────────
    avg_price = (req.min_price + req.max_price) / 2.0
    
    if req.price <= req.min_price:
        verdict = "BUY"
        message = "Best time to buy. Price is near lowest."
        suggested = req.min_price
    elif req.price <= avg_price:
        verdict = "CONSIDER"
        message = "Price is below average. Might be a good deal."
        suggested = req.min_price * 1.05
    else:
        verdict = "WAIT"
        message = "Price is moderate or high. You might get a better deal later."
        suggested = req.min_price * 1.05

    return AnalyzeResponse(
        verdict=verdict,
        message=message,
        suggested_price=suggested,
    )


# ── POST /api/v1/ai/predict — Price Trajectory Prediction ───────────────────

class PredictRequest(BaseModel):
    product_name: str = Field(..., max_length=MAX_PRODUCT_NAME_LEN)
    current_price: float
    price_history: list = Field(default=[])   # [{date, price}, ...]
    period: int = Field(default=30, ge=1, le=365)
    category: str = Field(default="General", max_length=MAX_CATEGORY_LEN)


@router.post("/predict")
async def predict_price(req: PredictRequest, request: Request):
    """
    Backend-only price prediction endpoint.
    Replaces frontend-side Gemini calls in aiSentinelService.js and priceService.js.
    Returns trend analysis + 7-day forward prediction.
    """
    # Rate limit: 20 AI requests per minute per IP
    rate_limiter.check(request, "ai-predict", max_requests=20, window_seconds=60)

    from app.utils.ai_logic import get_ai_prediction_trajectory

    if not req.product_name.strip():
        raise HTTPException(status_code=400, detail="product_name cannot be empty")
    if req.current_price <= 0:
        raise HTTPException(status_code=400, detail="current_price must be positive")
    if len(req.price_history) > MAX_PRICE_HISTORY_LEN:
        raise HTTPException(status_code=400, detail=f"price_history limited to {MAX_PRICE_HISTORY_LEN} entries")

    # If price_history is provided and has enough data, use Gemini for prediction
    if len(req.price_history) >= 5 and settings.GEMINI_API_KEY:
        try:
            from google import genai
            import asyncio as _asyncio

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            recent = req.price_history[-14:]

            from datetime import datetime, timedelta, timezone
            today = datetime.now(timezone.utc).date().isoformat()

            prompt = f"""You are a financial analysis AI for Indian e-commerce.
Analyze this price history for {req.product_name} and respond in JSON only.

Price data: {json.dumps(recent)}

Respond ONLY with valid JSON, no markdown:
{{
  "trend": "bullish | bearish | sideways",
  "trendStrength": "weak | moderate | strong",
  "supportLevel": <number>,
  "resistanceLevel": <number>,
  "predictedPrices": [
    {{ "date": "YYYY-MM-DD", "price": <number>, "confidence": "low | medium | high" }}
  ],
  "summary": "<2-3 sentence plain English analysis>",
  "riskLevel": "low | medium | high",
  "keyInsights": ["<insight 1>", "<insight 2>", "<insight 3>"]
}}

predictedPrices must contain next 7 days of predictions starting from tomorrow.
Base predictions ONLY on the mathematical trend of the provided data."""

            response = await _asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
            )
            text = (response.text or "").strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            parsed = json.loads(text.strip())

            # Validate required fields
            required = ["trend", "trendStrength", "supportLevel", "resistanceLevel", "predictedPrices", "summary", "riskLevel", "keyInsights"]
            if all(k in parsed for k in required):
                return parsed

        except Exception as e:
            logger.warning(f"[AI/predict] Gemini failed ({e}), using fallback")

    # Fallback: use the existing deterministic trajectory generator
    result = await get_ai_prediction_trajectory(
        product_name=req.product_name,
        current_price=req.current_price,
        category=req.category,
        days=req.period,
    )

    # Convert to the format expected by frontend
    prices = [p.get("price", 0) for p in req.price_history if isinstance(p, dict) and p.get("price")]
    current = prices[-1] if prices else req.current_price
    oldest = prices[0] if prices else req.current_price
    change_pct = ((current - oldest) / (oldest + 0.01)) * 100

    trend = result.get("trend", "sideways")
    trend_strength = result.get("trendStrength", "moderate")

    return {
        "trend": trend,
        "trendStrength": trend_strength,
        "supportLevel": min(prices) if prices else round(req.current_price * 0.85),
        "resistanceLevel": max(prices) if prices else round(req.current_price * 1.15),
        "predictedPrices": result.get("predictedPrices", []),
        "summary": result.get("summary", f"Analysis for {req.product_name} based on {len(prices)} data points."),
        "riskLevel": "high" if abs(change_pct) > 15 else "medium" if abs(change_pct) > 5 else "low",
        "keyInsights": [
            f"Price has {'increased' if change_pct > 0 else 'decreased'} by {abs(change_pct):.1f}%",
            f"Current support: ₹{min(prices):,.0f}" if prices else "Insufficient history",
            f"Current resistance: ₹{max(prices):,.0f}" if prices else "Insufficient history",
        ],
        "isFallback": True,
    }


# ── POST /api/v1/ai/mrp-analyze — MRP Analysis for Indian Market ────────────

class MRPAnalyzeRequest(BaseModel):
    product_name: str = Field(..., max_length=MAX_PRODUCT_NAME_LEN)
    category: str = Field(..., max_length=MAX_CATEGORY_LEN)
    cost_of_production: float
    target_market: str = Field(..., max_length=100)
    brand_tier: str = Field(..., max_length=50)
    key_features: str = Field(default="", max_length=MAX_TEXT_FIELD_LEN)
    competitor_prices: str = Field(default="", max_length=MAX_TEXT_FIELD_LEN)


@router.post("/mrp-analyze")
async def mrp_analyze(req: MRPAnalyzeRequest, request: Request):
    """
    Backend-only MRP analysis endpoint.
    Replaces frontend-side Gemini calls in MRPAnalyzerSentinel.jsx.
    """
    # Rate limit: 20 AI requests per minute per IP
    rate_limiter.check(request, "ai-mrp", max_requests=20, window_seconds=60)

    if not req.product_name.strip():
        raise HTTPException(status_code=400, detail="product_name cannot be empty")
    if not req.category.strip():
        raise HTTPException(status_code=400, detail="category cannot be empty")
    if req.cost_of_production <= 0:
        raise HTTPException(status_code=400, detail="cost_of_production must be positive")

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        # Return a basic calculation-based fallback
        cost = req.cost_of_production
        multipliers = {
            "Luxury": 4.0, "Premium": 3.0, "Established": 2.5,
            "Mid-tier": 2.0, "Budget": 1.5, "New": 1.8,
        }
        mult = multipliers.get(req.brand_tier, 2.0)
        return {
            "mrpRange": {
                "min": round(cost * (mult * 0.8)),
                "optimal": round(cost * mult),
                "max": round(cost * (mult * 1.3)),
            },
            "pricingStrategy": f"Cost-plus pricing for {req.brand_tier} tier in {req.target_market} market.",
            "grossMarginAtOptimal": f"{((mult - 1) / mult * 100):.0f}%",
            "gstSlab": "18% (estimated for general goods)",
            "marketPositioning": f"{req.brand_tier} positioning in the {req.target_market} segment.",
            "implementationTips": [
                "Validate with local market research",
                "Consider seasonal pricing adjustments",
                "Configure GEMINI_API_KEY for AI-powered analysis",
            ],
            "isFallback": True,
        }

    try:
        from google import genai
        import asyncio as _asyncio

        client = genai.Client(api_key=api_key)

        prompt = f"""You are a pricing strategy expert for the Indian retail market.
Product: {req.product_name}, Category: {req.category}, Cost: ₹{req.cost_of_production}, Market: {req.target_market}, Brand: {req.brand_tier}, USP: {req.key_features}
Competitors: {req.competitor_prices}

Respond ONLY in JSON format, no markdown, no explanation:
{{
  "mrpRange": {{
    "min": <number>,
    "optimal": <number>,
    "max": <number>
  }},
  "pricingStrategy": "<string>",
  "grossMarginAtOptimal": "<string>",
  "gstSlab": "<string>",
  "marketPositioning": "<string>",
  "implementationTips": [
    "<tip 1>",
    "<tip 2>",
    "<tip 3>"
  ]
}}

Note: Consider Indian market dynamics, GST implications, and competitive pricing."""

        response = await _asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = (response.text or "").strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        return json.loads(text.strip())

    except Exception as e:
        logger.error(f"[AI/mrp-analyze] Gemini failed: {e}")
        raise HTTPException(status_code=503, detail="AI analysis service temporarily unavailable")
=======
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
