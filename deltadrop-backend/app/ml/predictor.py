"""
DeltaDrop Price Predictor — ML model for price forecasting and buy/wait verdict.

Algorithm:
  1. Loads price history from PostgreSQL (last 90 days)
  2. Engineers time-series features (trend, seasonality, volatility, all-time-low proximity)
  3. Uses a RandomForestRegressor + GradientBoostingRegressor ensemble
  4. Outputs: predicted_price, confidence, horizon_days, verdict (BUY_NOW | WAIT | NEUTRAL)
"""

import logging
import os
import pickle
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_percentage_error

from app.core.config import settings

logger = logging.getLogger(__name__)

# Confidence thresholds
CONFIDENCE_BUY_NOW = 0.72   # above → BUY NOW
CONFIDENCE_WAIT    = 0.60   # below → NEUTRAL, between → WAIT


class PricePredictor:
    """
    Ensemble ML model for price trajectory prediction.
    Trained per-product using its historical price data.
    """

    def __init__(self):
        self.model_path = settings.ML_MODEL_PATH
        self._global_model: Optional[Pipeline] = None
        self._load_or_train_global_model()

    # ── Public interface ──────────────────────────────────────────────────────

    def predict(
        self,
        price_history: list[dict],   # [{price, recorded_at, retailer}, ...]
        current_price: float,
        horizon_days:  int = 14,
    ) -> dict:
        """
        Main prediction entry point.
        Returns a structured prediction dict ready to store in DB.
        """
        if len(price_history) < settings.ML_MIN_HISTORY_POINTS:
            return self._insufficient_data_verdict(current_price)

        try:
            df = self._build_features(price_history)
            if df.empty:
                return self._insufficient_data_verdict(current_price)

            predicted_price, confidence = self._run_prediction(df, current_price, horizon_days)
            verdict, reasoning          = self._compute_verdict(
                df, current_price, predicted_price, confidence
            )

            return {
                "predicted_price": round(predicted_price, 2),
                "predicted_low":   round(predicted_price * 0.95, 2),
                "predicted_high":  round(predicted_price * 1.05, 2),
                "confidence":      round(confidence, 4),
                "horizon_days":    horizon_days,
                "verdict":         verdict,
                "reasoning":       reasoning,
                "model_version":   "v1_ensemble",
            }

        except Exception as e:
            logger.error(f"[Predictor] Prediction error: {e}", exc_info=True)
            return self._insufficient_data_verdict(current_price)

    # ── Feature engineering ───────────────────────────────────────────────────

    def _build_features(self, price_history: list[dict]) -> pd.DataFrame:
        df = pd.DataFrame(price_history)
        df["recorded_at"] = pd.to_datetime(df["recorded_at"])
        df = df.sort_values("recorded_at").reset_index(drop=True)
        df["price"] = df["price"].astype(float)

        # Time features
        df["day_of_week"]  = df["recorded_at"].dt.dayofweek
        df["day_of_month"] = df["recorded_at"].dt.day
        df["month"]        = df["recorded_at"].dt.month
        df["days_since_first"] = (df["recorded_at"] - df["recorded_at"].min()).dt.days

        # Price features
        df["price_7d_ma"]  = df["price"].rolling(min(7,  len(df)), min_periods=1).mean()
        df["price_14d_ma"] = df["price"].rolling(min(14, len(df)), min_periods=1).mean()
        df["price_30d_ma"] = df["price"].rolling(min(30, len(df)), min_periods=1).mean()
        df["price_7d_std"] = df["price"].rolling(min(7,  len(df)), min_periods=1).std().fillna(0)

        # Trend features
        df["price_1d_chg"]  = df["price"].pct_change(1).fillna(0)
        df["price_7d_chg"]  = df["price"].pct_change(min(7,  len(df)-1)).fillna(0)
        df["price_30d_chg"] = df["price"].pct_change(min(30, len(df)-1)).fillna(0)

        # All-time low / high proximity
        df["all_time_low"]  = df["price"].expanding().min()
        df["all_time_high"] = df["price"].expanding().max()
        df["pct_from_atl"]  = (df["price"] - df["all_time_low"])  / (df["all_time_low"]  + 1)
        df["pct_from_ath"]  = (df["all_time_high"] - df["price"]) / (df["all_time_high"] + 1)

        # Volatility (coefficient of variation)
        df["volatility"] = df["price_7d_std"] / (df["price_7d_ma"] + 1)

        # Momentum
        df["momentum_3d"] = df["price"] - df["price"].shift(min(3, len(df)-1)).fillna(df["price"])
        df["momentum_7d"] = df["price"] - df["price"].shift(min(7, len(df)-1)).fillna(df["price"])

        return df.dropna()

    def _run_prediction(self, df: pd.DataFrame, current_price: float, horizon_days: int):
        feature_cols = [
            "day_of_week","day_of_month","month","days_since_first",
            "price_7d_ma","price_14d_ma","price_30d_ma","price_7d_std",
            "price_1d_chg","price_7d_chg","price_30d_chg",
            "pct_from_atl","pct_from_ath","volatility",
            "momentum_3d","momentum_7d",
        ]
        available = [c for c in feature_cols if c in df.columns]
        X         = df[available].values
        y         = df["price"].values

        if len(X) < 3:
            # Not enough rows for split — use simple trend extrapolation
            trend           = float(y[-1] - y[0]) / len(y)
            predicted_price = current_price + (trend * horizon_days * 0.5)
            return max(predicted_price, current_price * 0.7), 0.55

        # Train/test split (80/20)
        split = max(1, int(len(X) * 0.8))
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        # Ensemble: RF + GBR
        rf  = RandomForestRegressor(n_estimators=80, max_depth=8, random_state=42, n_jobs=-1)
        gbr = GradientBoostingRegressor(n_estimators=80, max_depth=4, learning_rate=0.08, random_state=42)

        rf.fit(X_train,  y_train)
        gbr.fit(X_train, y_train)

        # Compute confidence from test error
        if len(X_test) >= 1:
            pred_test = (rf.predict(X_test) + gbr.predict(X_test)) / 2
            mape      = mean_absolute_percentage_error(y_test, pred_test)
            confidence = max(0.30, min(0.98, 1.0 - mape))
        else:
            confidence = 0.60

        # Predict next N steps by rolling last row features
        last_row  = X[-1:].copy()
        last_days = int(df["days_since_first"].iloc[-1])

        future_preds = []
        for step in range(1, horizon_days + 1):
            row = last_row.copy()
            # Update time-based features (simple approximation)
            day_idx = available.index("days_since_first") if "days_since_first" in available else -1
            if day_idx >= 0:
                row[0][day_idx] = last_days + step
            rf_pred  = float(rf.predict(row)[0])
            gbr_pred = float(gbr.predict(row)[0])
            future_preds.append((rf_pred + gbr_pred) / 2)

        predicted_price = float(np.mean(future_preds))
        predicted_price = max(predicted_price, current_price * 0.6)  # floor at -40%
        predicted_price = min(predicted_price, current_price * 1.3)  # cap at +30%

        return predicted_price, confidence

    # ── Verdict logic ─────────────────────────────────────────────────────────

    def _compute_verdict(
        self,
        df: pd.DataFrame,
        current_price: float,
        predicted_price: float,
        confidence: float,
    ) -> tuple[str, str]:
        """
        Determines BUY_NOW, WAIT, or NEUTRAL based on:
        - Predicted price vs current price
        - Distance from all-time low
        - Trend direction
        - Confidence score
        """
        atl     = float(df["price"].min())
        trend   = float(df["price_7d_chg"].iloc[-1]) if "price_7d_chg" in df.columns else 0
        pct_atl = (current_price - atl) / (atl + 1) * 100  # % above all-time low

        expected_drop = (current_price - predicted_price) / (current_price + 1) * 100

        if confidence >= CONFIDENCE_BUY_NOW:
            if pct_atl <= 5.0:
                verdict   = "BUY_NOW"
                reasoning = (f"Current price of ₹{current_price:,.0f} is within 5% of the "
                             f"all-time low of ₹{atl:,.0f}. "
                             f"Our model has {confidence*100:.0f}% confidence this is the floor. "
                             "Strong buy signal — do not wait.")
            elif expected_drop < -5.0:
                verdict   = "BUY_NOW"
                reasoning = (f"7-day trend shows upward momentum. "
                             f"Model predicts price rising to ₹{predicted_price:,.0f} over {14} days. "
                             "Buy now before the price increases further.")
            else:
                verdict   = "WAIT"
                reasoning = (f"Model predicts a ₹{max(0, current_price-predicted_price):,.0f} "
                             f"({abs(expected_drop):.1f}%) reduction in the next 14 days. "
                             f"Current price is ₹{pct_atl:.1f}% above all-time low of ₹{atl:,.0f}. "
                             "Wait for a better entry point.")
        elif confidence >= CONFIDENCE_WAIT:
            verdict = "WAIT"
            if expected_drop > 3.0:
                reasoning = (f"Moderate confidence ({confidence*100:.0f}%) that price will drop "
                             f"₹{expected_drop:.1f}% in the next 14 days. "
                             "Watch this product and set an alert.")
            else:
                reasoning = ("Price has been stable. Limited signals for significant movement. "
                             "Set a target alert and monitor.")
        else:
            verdict   = "NEUTRAL"
            reasoning = ("Insufficient price history for a high-confidence prediction. "
                         f"Current price is ₹{pct_atl:.1f}% above the tracked low of ₹{atl:,.0f}. "
                         "Track this product to build better data.")

        return verdict, reasoning

    # ── Fallback ──────────────────────────────────────────────────────────────

    @staticmethod
    def _insufficient_data_verdict(current_price: float) -> dict:
        return {
            "predicted_price": current_price,
            "predicted_low":   current_price * 0.95,
            "predicted_high":  current_price * 1.05,
            "confidence":      0.1,
            "horizon_days":    7,
            "verdict":         "NEUTRAL",
            "reasoning":       "Collecting price history. AI trajectory is being generated.",
            "model_version":   "v1_insufficient_data",
            "trajectory":      [current_price] * 7
        }

    def _load_or_train_global_model(self):
        """Load pre-trained global model if it exists."""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    self._global_model = pickle.load(f)
                logger.info(f"[Predictor] Loaded model from {self.model_path}")
            except Exception as e:
                logger.warning(f"[Predictor] Could not load model: {e}")


# ── Async wrapper for FastAPI ─────────────────────────────────────────────────

async def run_prediction_for_product(product_id: int, db: Optional[AsyncSession] = None) -> Optional[dict]:
    """
    Fetch price history from DB and run prediction.
    Stores result in price_predictions table.
    """
    from app.models.product import PriceHistory, PricePrediction, Product
    from sqlalchemy import select
    from datetime import datetime, timezone
    from app.db.session import AsyncSessionLocal 

    # Always ensure we have a session (background tasks need their own)
    is_local_session = False
    if db is None:
        db = AsyncSessionLocal()
        is_local_session = True

    try:
        # Fetch history
        result = await db.execute(
            select(PriceHistory)
            .where(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.recorded_at.desc())
        )
        history = result.scalars().all()

        raw_history = [
            {"price": float(h.price), "recorded_at": h.recorded_at.isoformat()}
            for h in history
        ]
        current_price = float(history[0].price) if history else 0.0

        if not history:
            prod_res = await db.execute(select(Product).where(Product.id == product_id))
            product = prod_res.scalar_one_or_none()
            if product:
                live_prices = [
                    float(listing.current_price)
                    for listing in (product.retailer_listings or [])
                    if listing.is_active and listing.current_price is not None
                ]
                if live_prices:
                    current_price = min(live_prices)
            
            # ALWAYS return a fallback prediction, never None
            fallback = price_predictor._insufficient_data_verdict(current_price)
            await db.commit()
            return fallback

        # Predict
        prediction = price_predictor.predict(raw_history, current_price)

        # ── AI Augmentation ──
        # If low confidence or insufficient data, call Gemini for a better guess
        if prediction.get("confidence", 0) < 0.2:
            from app.models.product import Product
            prod_res = await db.execute(select(Product).where(Product.id == product_id))
            product  = prod_res.scalar_one_or_none()
            
            if product:
                from app.utils.ai_logic import get_ai_prediction_trajectory
                ai_data = await get_ai_prediction_trajectory(
                    product.name, current_price, product.category.value
                )
                if ai_data and "trajectory" in ai_data:
                    prediction["predicted_price"] = float(ai_data["trajectory"][-1])
                    prediction["confidence"]      = float(ai_data.get("confidence", 0.6))
                    prediction["reasoning"]       = f"AI ANALYSIS: {ai_data.get('reasoning')}"
                    prediction["model_version"]   = "v1_gemini_augmented"
                    prediction["trajectory"]      = ai_data["trajectory"]
                    if ai_data["trajectory"][-1] < current_price:
                        prediction["verdict"] = "WAIT"
                    elif ai_data["trajectory"][-1] > current_price * 1.05:
                        prediction["verdict"] = "BUY_NOW"

        # Store in DB
        # Note: Since the DB schema doesn't have a 'trajectory' column yet,
        # we append the trajectory to the reasoning field as a JSON string
        # for the frontend to pick up.
        final_reasoning = prediction.get("reasoning", "")
        if prediction.get("trajectory"):
            import json
            final_reasoning += f" | TRAJECTORY: {json.dumps(prediction['trajectory'])}"

        pred_record = PricePrediction(
            product_id      = product_id,
            predicted_price = prediction["predicted_price"],
            predicted_low   = prediction.get("predicted_low", prediction["predicted_price"] * 0.95),
            predicted_high  = prediction.get("predicted_high", prediction["predicted_price"] * 1.05),
            confidence      = prediction["confidence"],
            horizon_days    = prediction["horizon_days"],
            verdict         = prediction["verdict"],
            reasoning       = final_reasoning,
            model_version   = prediction["model_version"],
            predicted_at    = datetime.now(timezone.utc),
        )
        db.add(pred_record)
        await db.commit()

        return prediction

    except Exception as e:
        logger.error(f"[Predictor] Failed for product {product_id}: {e}")
        fallback = price_predictor._insufficient_data_verdict(0.0)
        try:
            db.add(PricePrediction(
                product_id      = product_id,
                predicted_price = fallback["predicted_price"],
                predicted_low   = fallback["predicted_low"],
                predicted_high  = fallback["predicted_high"],
                confidence      = fallback["confidence"],
                horizon_days    = fallback["horizon_days"],
                verdict         = fallback["verdict"],
                reasoning       = fallback["reasoning"],
                model_version   = fallback["model_version"],
                predicted_at    = datetime.now(timezone.utc),
            ))
            await db.commit()
        except Exception:
            pass
        return fallback
    finally:
        if is_local_session:
            await db.close()


# Singleton
price_predictor = PricePredictor()
