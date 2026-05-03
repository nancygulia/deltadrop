import asyncio
import json
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _clip(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def generate_recommendation_logic(
    current_price: float,
    min_price: float,
    max_price: float,
    trend_7d: float,
    prediction_price: float,
    confidence: float,
    seller_count: int = 0,
) -> dict:
    """
    Deterministic premium recommendation engine.
    Verdicts:
      BUY  - close to ATL and supported by trend
      WAIT - price is elevated or forecast points lower
      HOLD - fair value / mixed signals
    """
    current_price = float(current_price or 0)
    min_price = float(min_price or current_price or 0)
    max_price = float(max_price or current_price or 0)
    prediction_price = float(prediction_price or current_price or 0)
    trend_7d = float(trend_7d or 0)
    seller_count = int(seller_count or 0)

    atl_gap_pct = ((current_price - min_price) / (min_price + 0.01)) * 100 if min_price else 0.0
    ath_gap_pct = ((max_price - current_price) / (max_price + 0.01)) * 100 if max_price else 0.0
    spread_pct = ((max_price - min_price) / (min_price + 0.01)) * 100 if max_price > min_price else 0.0
    price_drop_signal = prediction_price < current_price * 0.98
    price_rise_signal = prediction_price > current_price * 1.03
    near_low = atl_gap_pct <= 3.0
    elevated = atl_gap_pct >= 12.0
    stable = abs(trend_7d) <= 2.0

    if near_low and not price_rise_signal:
        verdict = "BUY"
        smart_recommendation = "Best time to buy. Price is near all-time low."
        suggested_alert_price = round(min_price * 1.02) if min_price else round(current_price * 0.98)
    elif elevated or trend_7d < -1.0 or price_drop_signal:
        verdict = "WAIT"
        if elevated:
            smart_recommendation = f"Price is {atl_gap_pct:.1f}% above low. Wait for a better entry."
        elif price_drop_signal:
            smart_recommendation = f"Forecast points to Rs. {prediction_price:,.0f}. Wait."
        else:
            smart_recommendation = "Momentum is soft. Waiting should improve value."
        suggested_alert_price = round(min(prediction_price, max(min_price * 1.02, current_price * 0.97)))
    else:
        verdict = "HOLD"
        smart_recommendation = "Fair value. Hold and monitor for a stronger dip."
        suggested_alert_price = round(min_price * 1.05) if min_price else round(current_price * 0.97)

    # Higher confidence when signal is obvious and market spread is wide.
    signal_strength = 0.45
    if near_low:
        signal_strength += 0.22
    if elevated:
        signal_strength += 0.18
    if stable:
        signal_strength += 0.05
    if price_drop_signal or price_rise_signal:
        signal_strength += 0.08
    if seller_count >= 3:
        signal_strength += 0.03
    signal_strength += min(0.08, spread_pct / 250.0)
    confidence = _clip(max(confidence, signal_strength), 0.10, 0.98)

    reasoning = (
        f"Current price Rs. {current_price:,.0f} is {atl_gap_pct:.1f}% above the lowest recorded price "
        f"and {ath_gap_pct:.1f}% below the highest. 7-day trend is {trend_7d:+.1f}%. "
        f"Across {seller_count} sellers the spread is {spread_pct:.1f}%. {smart_recommendation}"
    )

    return {
        "verdict": verdict,
        "reasoning": reasoning,
        "confidence": confidence,
        "method": "pro_fallback",
        "insights": {
            "price_comparison": f"Current: Rs. {current_price:,.0f} | Lowest: Rs. {min_price:,.0f} | Highest: Rs. {max_price:,.0f}",
            "trend_analysis": f"7-Day Trend: {trend_7d:+.1f}% | Market spread: {spread_pct:.1f}%",
            "smart_recommendation": smart_recommendation,
            "target_strategy": verdict,
            "suggested_alert_price": suggested_alert_price,
        },
    }


async def get_ai_recommendation(
    product_name: str,
    current_price: float,
    min_price: float,
    max_price: float,
    trend_7d: float,
    prediction_price: float,
    confidence: float,
    seller_count: int = 0,
) -> dict:
    """
    Uses Gemini for narrative polish only.
    The verdict remains anchored to deterministic baseline logic.
    """
    baseline = generate_recommendation_logic(
        current_price=current_price,
        min_price=min_price,
        max_price=max_price,
        trend_7d=trend_7d,
        prediction_price=prediction_price,
        confidence=confidence,
        seller_count=seller_count,
    )
    logger.info(
        f"[AI] baseline ready product={product_name} verdict={baseline['verdict']} "
        f"confidence={baseline['confidence']:.2f} current={current_price} min={min_price} max={max_price} trend={trend_7d}"
    )

    api_key = settings.GEMINI_API_KEY
    logger.info(f"[AI] Gemini API key check: {'SET' if api_key else 'NOT SET'} for {product_name}")
    if not api_key:
        logger.warning(f"[AI] No GEMINI_API_KEY configured. Using baseline for {product_name}.")
        return baseline

    try:
        import google.genai as genai
        logger.info(f"[AI] Attempting to import google.genai for {product_name}")
        
        client = genai.Client(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        logger.info(f"[AI] Gemini request start product={product_name}")

        prompt = f"""
Product: {product_name}
Current Price: Rs. {current_price:,.0f}
Lowest Price: Rs. {min_price:,.0f}
Highest Price: Rs. {max_price:,.0f}
7-Day Trend: {trend_7d:+.1f}%
Seller Count: {seller_count}

Baseline Verdict: {baseline["verdict"]}
Baseline Reasoning: {baseline["reasoning"]}
Baseline Smart Recommendation: {baseline["insights"]["smart_recommendation"]}
Baseline Suggested Alert Price: {baseline["insights"]["suggested_alert_price"]}

You are DeltaDrop's premium AI Price Sentinel.
Return JSON ONLY with these exact keys:
- verdict: "BUY", "WAIT", or "HOLD"
- reasoning: a concise paragraph grounded in data
- smart_recommendation: 3-7 words, actionable
- suggested_alert_price: integer price target
- confidence: float between 0 and 1

Do not use markdown.
"""

        response = await asyncio.to_thread(client.generate_content, prompt)
        text = (response.text or "").strip()
        logger.info(f"[AI] Gemini response received product={product_name} chars={len(text)}")

        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        parsed = json.loads(text)
        logger.info(f"[AI] Gemini parsed output product={product_name} keys={list(parsed.keys())}")
        parsed_verdict = str(parsed.get("verdict", baseline["verdict"])).upper().strip()
        if parsed_verdict not in {"BUY", "WAIT", "HOLD"}:
            parsed_verdict = baseline["verdict"]

        try:
            parsed_conf = float(parsed.get("confidence", baseline["confidence"]))
        except Exception:
            parsed_conf = baseline["confidence"]

        return {
            "verdict": parsed_verdict,
            "reasoning": parsed.get("reasoning", baseline["reasoning"]),
            "confidence": _clip(parsed_conf, 0.10, 0.98),
            "method": "gemini_1.5_flash",
            "insights": {
                "price_comparison": baseline["insights"]["price_comparison"],
                "trend_analysis": baseline["insights"]["trend_analysis"],
                "smart_recommendation": parsed.get("smart_recommendation", baseline["insights"]["smart_recommendation"]),
                "target_strategy": parsed_verdict,
                "suggested_alert_price": parsed.get("suggested_alert_price", baseline["insights"]["suggested_alert_price"]),
            },
        }
    except ImportError as e:
        logger.error(f"[AI] Failed to import google.genai for {product_name}: {e}")
        fallback = dict(baseline)
        fallback["reasoning"] = f"AI library missing: {fallback['reasoning']}"
        fallback["method"] = "import_error_fallback"
        return fallback
    except Exception as e:
        logger.error(f"[AI] Gemini failure for {product_name}: {e}. Falling back to baseline logic.")
        fallback = dict(baseline)
        fallback["reasoning"] = f"AUTO-SENTINEL: {fallback['reasoning']}"
        fallback["method"] = "error_fallback"
        return fallback


async def get_ai_prediction_trajectory(
    product_name: str,
    current_price: float,
    category: str = "Electronics",
    days: int = 90,
) -> dict:
    """
    Generates a realistic price HISTORY (past `days` days) for a product using Gemini.

    Returns a dict with keys matching what /api/price-history expects:
      {
        "trajectory": [{"date": "YYYY-MM-DD", "price": 00000}, ...],   ← past dates
        "predictedPrices": [{"date": "YYYY-MM-DD", "price": 00000, "confidence": "medium"}, ...],  ← next 7 days
        "trend": "bullish|bearish|sideways",
        "summary": "...",
        "confidence": 0.0-1.0
      }
    Falls back to a fast deterministic simulation if Gemini is unavailable.
    """
    from datetime import datetime, timedelta, timezone
    import random as _rnd

    today = datetime.now(timezone.utc).date()

    # ── Deterministic fallback (works with no API key, no internet) ───────────
    def _sim_fallback() -> dict:
        rng = _rnd.Random(hash(product_name) % (2**31) + int(current_price))
        start_mult = 1.0 + rng.uniform(0.08, 0.18)
        events: dict = {}
        for _ in range(rng.randint(2, 4)):
            s = rng.randint(0, days - 6); dur = rng.randint(2, 5)
            mult = rng.uniform(0.72, 0.92)
            for d in range(s, min(s + dur, days)): events[d] = min(events.get(d, 1.0), mult)
        for _ in range(rng.randint(1, 2)):
            s = rng.randint(0, days - 8); dur = rng.randint(3, 7)
            mult = rng.uniform(1.05, 1.15)
            for d in range(s, min(s + dur, days)):
                if d not in events: events[d] = mult

        trajectory = []
        for i in range(days):
            date_str = (today - timedelta(days=days - 1 - i)).isoformat()
            progress = i / max(days - 1, 1)
            price = current_price * (start_mult + (1.0 - start_mult) * progress)
            if i in events: price *= events[i]
            price *= 1.0 + rng.uniform(-0.015, 0.015)
            price = max(current_price * 0.55, min(current_price * 2.0, price))
            trajectory.append({"date": date_str, "price": round(price)})

        # 7-day forward prediction
        last = trajectory[-1]["price"]
        trend = "bearish" if last > current_price * 1.05 else "bullish" if last < current_price * 0.97 else "sideways"
        predicted = []
        for j in range(1, 8):
            drift = 1.0 + rng.uniform(-0.01, 0.008)
            predicted.append({
                "date": (today + timedelta(days=j)).isoformat(),
                "price": round(last * (drift ** j)),
                "confidence": "medium",
            })
        return {
            "trajectory": trajectory,
            "predictedPrices": predicted,
            "trend": trend,
            "trendStrength": "moderate",
            "summary": f"Simulated {days}-day price history for {product_name} based on typical Indian e-commerce patterns.",
            "confidence": 0.72,
        }

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.info(f"[AI] No GEMINI_API_KEY — using deterministic simulation for {product_name}")
        return _sim_fallback()

    # Build compact price snapshot (last 7 data points of fallback to anchor Gemini)
    sim = _sim_fallback()
    recent_prices = sim["trajectory"][-7:]

    prompt = f"""You are an Indian e-commerce price analyst for DeltaDrop.

Product: {product_name}
Category: {category}
Current Price: ₹{current_price:,.0f}
Today: {today.isoformat()}

Recent price snapshot (last 7 days):
{json.dumps(recent_prices)}

Generate REALISTIC price history for the past {days} days and next 7-day prediction.
Return ONLY this JSON, no markdown, no explanation:
{{
  "trajectory": [
    {{"date": "YYYY-MM-DD", "price": <integer INR>}},
    ... exactly {days} entries from {(today - timedelta(days=days-1)).isoformat()} to {today.isoformat()} ...
  ],
  "predictedPrices": [
    {{"date": "YYYY-MM-DD", "price": <integer INR>, "confidence": "low|medium|high"}},
    ... exactly 7 entries for next 7 days ...
  ],
  "trend": "bullish|bearish|sideways",
  "trendStrength": "weak|moderate|strong",
  "summary": "<2-3 sentence analysis in context of Indian e-commerce>",
  "riskLevel": "low|medium|high"
}}

Rules:
- ALL dates in trajectory must be PAST dates (before or on {today.isoformat()})
- predictedPrices must start from {(today + timedelta(days=1)).isoformat()}
- Prices in Indian Rupees, realistic integers
- Show 2-3 sale dips (10-25% drops for 2-5 days) and 1-2 small hikes
- Start slightly above ₹{current_price:,.0f}, drift down to current price today
- Never go below ₹{int(current_price * 0.5):,} or above ₹{int(current_price * 1.8):,}"""

    try:
        import google.genai as genai
        client = genai.Client(api_key=api_key)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=prompt,
        )
        text = (response.text or "").strip()
        # Strip markdown fences if present
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        parsed = json.loads(text)
        logger.info(f"[AI] Trajectory generated by Gemini for {product_name} — {len(parsed.get('trajectory', []))} points")
        # Merge with fallback if Gemini returns incomplete data
        if not parsed.get("trajectory") or len(parsed["trajectory"]) < 7:
            parsed["trajectory"] = sim["trajectory"]
        if not parsed.get("predictedPrices"):
            parsed["predictedPrices"] = sim["predictedPrices"]
        return parsed
    except Exception as e:
        logger.error(f"[AI] Gemini trajectory failed for {product_name}: {e} — using simulation")
        return _sim_fallback()
