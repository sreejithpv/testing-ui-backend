"""
Stock Scanner Module
=====================
Analyzes stock data to find breakout candidates and trend reversals.

WHAT IS A BREAKOUT?
    A breakout happens when a stock's price pushes through a resistance level
    (a price ceiling it kept bouncing off). Before the breakout, the price
    often "squeezes" into a very tight range — like compressing a spring.
    When it snaps, the move can be explosive.

    We look for: tight Bollinger Bands, rising volume, RSI building momentum.

WHAT IS A TREND REVERSAL?
    A trend reversal is when a stock changes direction:
    - Bullish reversal: Was going DOWN → now turning UP  (potential buy)
    - Bearish reversal: Was going UP   → now turning DOWN (potential sell/short)

    We look for: RSI extremes, MACD crossovers, EMA crossovers.

PYTHON CONCEPTS:
    - "list comprehension" like [x for x in items if x > 0] filters a list
    - "lambda" is a tiny inline function: lambda x: x["price"] → returns the price
    - "sort(key=..., reverse=True)" sorts a list by any field you choose
"""

import logging
from typing import Optional

import pandas as pd
import numpy as np

from indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_atr,
    calculate_vwap,
)
import config

logger = logging.getLogger(__name__)


def _safe_float(series: pd.Series, index: int = -1, default: float = 0.0) -> float:
    """
    Safely get a float value from a pandas Series at the given index.
    Returns `default` if the value is NaN or the index is out of range.

    Why we need this:
    - Technical indicators produce NaN for the first few bars (not enough data yet)
    - Accessing .iloc[-1] on an empty Series would crash
    - This prevents the whole scan from failing because of one bad value
    """
    try:
        if series is None or series.empty:
            return default
        val = series.iloc[index]
        return float(val) if not pd.isna(val) else default
    except (IndexError, TypeError):
        return default


def analyze_stock(ticker: str, df: pd.DataFrame) -> Optional[dict]:
    """
    Run full technical analysis on a single stock.

    This is the core function that:
    1. Calculates all technical indicators (EMA, RSI, MACD, Bollinger Bands)
    2. Scores the stock for BREAKOUT potential (0-100)
    3. Scores the stock for TREND REVERSAL potential (0-100)
    4. Returns a dictionary with all the data the frontend needs

    Args:
        ticker: Stock symbol (e.g., "AAPL")
        df:     DataFrame with columns [Open, High, Low, Close, Volume]

    Returns:
        Dictionary with analysis results, or None if analysis failed.
        Example:
        {
            "ticker": "AAPL",
            "price": 185.50,
            "pct_change": 1.23,
            "volume": 5200000,
            "breakout_score": 65,
            "breakout_signals": ["BB Squeeze", "Vol Surge (2.1x)"],
            "reversal_score": 40,
            "reversal_signals": ["MACD Bullish Cross"],
            "reversal_direction": "bullish",
            ...
        }
    """
    try:
        # ── Extract the price/volume columns from the DataFrame ──
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # ── Current values (most recent bar) ──
        current_price = float(close.iloc[-1])
        prev_price = float(close.iloc[-2]) if len(close) > 1 else current_price
        current_volume = float(volume.iloc[-1])

        # Price change from bar to bar (most recent move)
        bar_pct_change = ((current_price - prev_price) / prev_price * 100) if prev_price else 0

        # Price change from the day's open to now
        day_open = float(df["Open"].iloc[0])
        day_pct_change = ((current_price - day_open) / day_open * 100) if day_open else 0

        # ═══════════════════════════════════════════════════════════════════
        # CALCULATE INDICATORS
        # ═══════════════════════════════════════════════════════════════════

        # EMAs for trend direction (9 = fast reaction, 21 = smoother)
        ema_9 = calculate_ema(close, 9)
        ema_21 = calculate_ema(close, 21)

        # RSI for momentum / overbought-oversold
        rsi = calculate_rsi(close, 14)
        current_rsi = _safe_float(rsi, -1, 50)

        # MACD for trend-change detection
        macd_line, signal_line, histogram = calculate_macd(close)
        current_hist = _safe_float(histogram, -1)
        prev_hist = _safe_float(histogram, -2)

        # Bollinger Bands for squeeze/breakout detection
        bb_upper, bb_middle, bb_lower, bb_bandwidth = calculate_bollinger_bands(close)
        current_bandwidth = _safe_float(bb_bandwidth, -1, 0.1)

        # Volume analysis: compare current volume to 20-bar average
        avg_volume = float(volume.rolling(window=20).mean().iloc[-1]) if len(volume) >= 20 else float(volume.mean())
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        # ATR for volatility context
        atr = calculate_atr(high, low, close)
        current_atr = _safe_float(atr, -1)

        # VWAP — "fair price" for the day weighted by volume
        # Price above VWAP = buyers in control (bullish intraday)
        # Price below VWAP = sellers in control (bearish intraday)
        vwap = calculate_vwap(high, low, close, volume)
        current_vwap = _safe_float(vwap, -1, current_price)

        # ═══════════════════════════════════════════════════════════════════
        # SCORE: BREAKOUT POTENTIAL (0 to 100)
        # ═══════════════════════════════════════════════════════════════════
        breakout_score = 0
        breakout_signals = []

        # 1. Bollinger Band Squeeze (0–30 points)
        #    Tight bands = stock is coiling up, breakout is likely
        if current_bandwidth < config.BB_SQUEEZE_THRESHOLD:
            squeeze_intensity = (config.BB_SQUEEZE_THRESHOLD - current_bandwidth) / config.BB_SQUEEZE_THRESHOLD
            points = min(30, int(squeeze_intensity * 30))
            breakout_score += points
            breakout_signals.append(f"BB Squeeze ({current_bandwidth:.3f})")

        # 2. Volume Surge (0–30 points)
        #    Big volume confirms that the breakout is real, not a fake-out
        if volume_ratio > config.VOLUME_SURGE_MULTIPLIER:
            points = min(30, int((volume_ratio - 1) * 15))
            breakout_score += points
            breakout_signals.append(f"Vol Surge ({volume_ratio:.1f}x)")

        # 3. Price near upper Bollinger Band (0–20 points)
        #    Price pressing against the upper band = pushing against resistance
        bb_upper_val = _safe_float(bb_upper, -1, current_price)
        bb_lower_val = _safe_float(bb_lower, -1, current_price)
        bb_range = bb_upper_val - bb_lower_val
        if bb_range > 0:
            # price_position: 0 = at lower band, 1 = at upper band
            price_position = (current_price - bb_lower_val) / bb_range
            if price_position > 0.7:
                breakout_score += int(price_position * 20)
                breakout_signals.append("Near Resistance")

        # 4. RSI Momentum (0–20 points)
        #    RSI in the "goldilocks zone" = momentum is building but NOT overbought yet
        if config.RSI_MOMENTUM_LOW <= current_rsi <= config.RSI_MOMENTUM_HIGH:
            # Peak score at RSI = 55 (right in the sweet spot)
            rsi_points = 20 - abs(current_rsi - 55)
            breakout_score += max(0, int(rsi_points))
            breakout_signals.append(f"RSI Momentum ({current_rsi:.0f})")

        # ═══════════════════════════════════════════════════════════════════
        # SCORE: TREND REVERSAL (0 to 100)
        # ═══════════════════════════════════════════════════════════════════
        # We calculate BOTH bullish and bearish scores, then pick the stronger one

        bullish_score = 0
        bullish_signals = []
        bearish_score = 0
        bearish_signals = []

        # 1. RSI Extremes (0–25 points)
        #    Very low RSI = oversold → might bounce up (bullish reversal)
        #    Very high RSI = overbought → might drop down (bearish reversal)
        if current_rsi < config.RSI_OVERSOLD:
            bullish_score += min(25, int((config.RSI_OVERSOLD - current_rsi) * 2))
            bullish_signals.append(f"RSI Oversold ({current_rsi:.0f})")
        elif current_rsi > config.RSI_OVERBOUGHT:
            bearish_score += min(25, int((current_rsi - config.RSI_OVERBOUGHT) * 2))
            bearish_signals.append(f"RSI Overbought ({current_rsi:.0f})")

        # 2. MACD Crossover (0–25 points)
        #    Histogram flipping from negative to positive = bullish crossover
        #    Histogram flipping from positive to negative = bearish crossover
        current_macd = _safe_float(macd_line, -1)
        current_signal = _safe_float(signal_line, -1)

        if current_macd > current_signal and prev_hist <= 0 < current_hist:
            bullish_score += 25
            bullish_signals.append("MACD Bullish Cross")
        elif current_macd < current_signal and prev_hist >= 0 > current_hist:
            bearish_score += 25
            bearish_signals.append("MACD Bearish Cross")

        # 3. EMA Crossover (0–25 points)
        #    Fast EMA (9) crossing above slow EMA (21) = short-term trend turning up
        #    Fast EMA (9) crossing below slow EMA (21) = short-term trend turning down
        curr_ema9 = _safe_float(ema_9, -1)
        curr_ema21 = _safe_float(ema_21, -1)
        prev_ema9 = _safe_float(ema_9, -2)
        prev_ema21 = _safe_float(ema_21, -2)

        if curr_ema9 > curr_ema21 and prev_ema9 <= prev_ema21:
            bullish_score += 25
            bullish_signals.append("EMA Bullish Cross")
        elif curr_ema9 < curr_ema21 and prev_ema9 >= prev_ema21:
            bearish_score += 25
            bearish_signals.append("EMA Bearish Cross")

        # 4. Histogram Momentum Shift (0–15 points)
        #    Histogram bars getting progressively larger in one direction
        if len(histogram) > 2:
            hist_2 = _safe_float(histogram, -3)
            if hist_2 < prev_hist < current_hist and current_hist > 0:
                bullish_score += 15
                bullish_signals.append("Momentum Shifting Up")
            elif hist_2 > prev_hist > current_hist and current_hist < 0:
                bearish_score += 15
                bearish_signals.append("Momentum Shifting Down")

        # ── Pick the dominant reversal direction ──
        reversal_score = 0
        reversal_signals = []
        reversal_direction = "none"

        if bullish_score > bearish_score and bullish_score > 10:
            reversal_score = bullish_score
            reversal_signals = bullish_signals
            reversal_direction = "bullish"
        elif bearish_score > bullish_score and bearish_score > 10:
            reversal_score = bearish_score
            reversal_signals = bearish_signals
            reversal_direction = "bearish"

        # ═══════════════════════════════════════════════════════════════════
        # TRADE LEVELS — Entry, Stop-Loss, Target based on ATR
        # ═══════════════════════════════════════════════════════════════════
        # ATR = Average True Range. It tells you how much a stock typically
        # moves per bar. We use it to set stop-loss and target distances
        # that match the stock's natural volatility.

        # EMA trend: is the fast EMA above the slow EMA?
        ema_trend = "bullish" if curr_ema9 > curr_ema21 else "bearish" if curr_ema9 < curr_ema21 else "neutral"

        # MACD direction: is the histogram positive or negative?
        macd_direction = "bullish" if current_hist > 0 else "bearish" if current_hist < 0 else "neutral"

        # VWAP position: is price above or below the fair value?
        vwap_signal = "above" if current_price > current_vwap else "below"

        # ── Calculate Entry / Stop / Target ──
        # For BULLISH: entry = now, stop = below, target = above
        # For BEARISH: entry = now, stop = above, target = below
        # Stop = 1.5× ATR from entry (tight enough to limit loss)
        # Target = 3× ATR from entry (gives 2:1 reward-to-risk)
        atr_for_levels = current_atr if current_atr > 0 else current_price * 0.01

        if reversal_direction == "bearish":
            stop_loss = round(current_price + 1.5 * atr_for_levels, 2)
            target = round(current_price - 3 * atr_for_levels, 2)
        else:
            # Default to bullish levels (also used for breakouts)
            stop_loss = round(current_price - 1.5 * atr_for_levels, 2)
            target = round(current_price + 3 * atr_for_levels, 2)

        risk = abs(current_price - stop_loss)
        reward = abs(target - current_price)
        risk_reward = round(reward / risk, 1) if risk > 0 else 0

        # ── Trade Action — combines ALL indicators into one verdict ──
        # Each bullish signal adds +1, each bearish signal adds -1
        action_score = 0
        if current_rsi < 30:
            action_score += 2       # strongly oversold = bullish
        elif current_rsi < 45:
            action_score += 1       # mildly oversold
        elif current_rsi > 70:
            action_score -= 2       # strongly overbought = bearish
        elif current_rsi > 55:
            action_score -= 1       # mildly overbought

        if ema_trend == "bullish":
            action_score += 1
        elif ema_trend == "bearish":
            action_score -= 1

        if macd_direction == "bullish":
            action_score += 1
        elif macd_direction == "bearish":
            action_score -= 1

        if vwap_signal == "above":
            action_score += 1
        else:
            action_score -= 1

        if volume_ratio > config.VOLUME_SURGE_MULTIPLIER:
            # Volume confirms the move in whatever direction
            if action_score > 0:
                action_score += 1
            elif action_score < 0:
                action_score -= 1

        # Map score to human-readable action
        if action_score >= 4:
            trade_action = "Strong Buy"
        elif action_score >= 2:
            trade_action = "Buy"
        elif action_score <= -4:
            trade_action = "Strong Sell"
        elif action_score <= -2:
            trade_action = "Sell"
        else:
            trade_action = "Hold"

        # ═══════════════════════════════════════════════════════════════════
        # RETURN ALL DATA
        # ═══════════════════════════════════════════════════════════════════
        return {
            "ticker": ticker,
            "price": round(current_price, 2),
            "pct_change": round(day_pct_change, 2),
            "volume": int(current_volume),
            "avg_volume": int(avg_volume),
            "volume_ratio": round(volume_ratio, 2),
            "rsi": round(current_rsi, 1),
            "macd": round(_safe_float(macd_line, -1), 4),
            "macd_histogram": round(current_hist, 4),
            "macd_direction": macd_direction,
            "bb_bandwidth": round(current_bandwidth, 4),
            "atr": round(current_atr, 4),
            "breakout_score": min(100, breakout_score),
            "breakout_signals": breakout_signals,
            "reversal_score": min(100, reversal_score),
            "reversal_signals": reversal_signals,
            "reversal_direction": reversal_direction,
            "ema_9": round(curr_ema9, 2),
            "ema_21": round(curr_ema21, 2),
            "ema_trend": ema_trend,
            "vwap": round(current_vwap, 2),
            "vwap_signal": vwap_signal,
            "stop_loss": stop_loss,
            "target": target,
            "risk_reward": risk_reward,
            "trade_action": trade_action,
        }

    except Exception as e:
        logger.error(f"Error analyzing {ticker}: {e}")
        return None


def scan_stocks(
    stock_data: dict,
    sort_by: str = None,
    sort_order: str = None,
    max_results: int = None,
) -> dict:
    """
    Main scanning function — analyzes all stocks and separates them into
    breakout candidates and trend reversal candidates.

    How it works:
    1. Loop through every stock in the data
    2. Run analyze_stock() on each one (calculates indicators + scores)
    3. Filter: keep only stocks with score > 0 for each category
    4. Sort by the chosen criteria (% change, score, or volume)
    5. Return the top N results for each category

    A stock CAN appear in BOTH lists if it has high scores for both
    breakout and reversal — this is valid and useful information.

    Args:
        stock_data:  Dictionary of {ticker: DataFrame} from data_provider
        sort_by:     Override config.SORT_BY ("pct_change", "score", "volume")
        sort_order:  Override config.SORT_ORDER ("asc" or "desc")
        max_results: Override config.MAX_RESULTS

    Returns:
        {
            "breakouts": [ {ticker, price, pct_change, score, signals, ...}, ... ],
            "reversals": [ {ticker, price, pct_change, score, signals, ...}, ... ],
        }
    """
    # Use provided values or fall back to config defaults
    sort_by = sort_by or config.SORT_BY
    sort_order = sort_order or config.SORT_ORDER
    max_results = max_results or config.MAX_RESULTS

    all_analyses = []

    # ── Step 1: Analyze every stock ──
    for ticker, df in stock_data.items():
        result = analyze_stock(ticker, df)
        if result is not None:
            all_analyses.append(result)

    if not all_analyses:
        return {"breakouts": [], "reversals": []}

    # ── Step 2: Filter into categories ──
    # Filter out low-volume tickers from both categories
    min_vol = getattr(config, "MIN_VOLUME", 10000)
    # breakout_score > 0 means the stock showed at least one breakout signal
    breakouts = [s for s in all_analyses if s["breakout_score"] > 0 and s["volume"] >= min_vol]
    # Reversal must have score > 0 AND minimum volume to filter fake/low-volume signals
    reversals = [
        s for s in all_analyses
        if s["reversal_score"] > 0 and s["volume"] >= min_vol
    ]

    # ── Step 3: Sort ──
    # Primary sort: trade_action priority (Strong Buy first, then Buy, etc.)
    # Secondary sort: by the chosen criteria within each action group
    _ACTION_RANK = {"Strong Buy": 0, "Buy": 1, "Hold": 2, "Sell": 3, "Strong Sell": 4}
    reverse = sort_order == "desc"  # True = highest first

    def _sort_key(x, score_field):
        action_rank = _ACTION_RANK.get(x.get("trade_action", "Hold"), 2)
        if sort_by == "pct_change":
            secondary = abs(x["pct_change"])
        elif sort_by == "score":
            secondary = x[score_field]
        elif sort_by == "volume":
            secondary = x["volume_ratio"]
        else:
            secondary = abs(x["pct_change"])
        # action_rank ascending (Strong Buy=0 first), secondary descending
        return (action_rank, -secondary if reverse else secondary)

    breakouts.sort(key=lambda x: _sort_key(x, "breakout_score"))
    reversals.sort(key=lambda x: _sort_key(x, "reversal_score"))

    # ── Step 3b: Split breakouts into upward (breakouts) and downward (breakdowns) ──
    breakouts_up = [s for s in breakouts if s["pct_change"] >= 0]
    breakdowns = [s for s in breakouts if s["pct_change"] < 0]

    # ── Step 3c: Split reversals into bullish and bearish ──
    bullish_reversals = [s for s in reversals if s["reversal_direction"] == "bullish"]
    bearish_reversals = [s for s in reversals if s["reversal_direction"] == "bearish"]

    # ── Step 4: Return top N ──
    return {
        "breakouts": breakouts_up[:max_results],
        "breakdowns": breakdowns[:max_results],
        "reversals": reversals[:max_results],
        "bullish_reversals": bullish_reversals[:max_results],
        "bearish_reversals": bearish_reversals[:max_results],
    }
