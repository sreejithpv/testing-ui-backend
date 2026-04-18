"""
Technical Indicators Module
============================
Contains functions to calculate common technical analysis indicators.
Each function takes pandas Series/DataFrames and returns computed values.

PYTHON BASICS FOR BEGINNERS:
─────────────────────────────
- A pandas "Series" is like a single column of numbers (e.g., all closing prices).
- A pandas "DataFrame" is like a spreadsheet table with multiple columns.
- .rolling(window=N) creates a "sliding window" that looks at the last N values.
  Example: .rolling(window=20).mean() → average of the last 20 values at each point.
- .ewm() creates an "exponentially weighted" window where recent values count more.
- .shift() moves data forward/backward by 1 step. close.shift() = yesterday's close.
- .diff() calculates the difference between consecutive values.
"""

import pandas as pd
import numpy as np


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """
    Exponential Moving Average (EMA)
    ---------------------------------
    Like a regular average, but gives MORE weight to recent prices.
    This makes it react faster to new price changes than a simple average.

    Traders use EMAs to identify trend direction:
    - Price above EMA → uptrend
    - Price below EMA → downtrend

    Common periods: 9 (fast), 21 (medium), 50 (slow)

    Args:
        series: Price data (usually closing prices)
        period: How many bars to look back (e.g., 9, 21)

    Returns:
        A Series of EMA values, one for each price point
    """
    # ewm = Exponentially Weighted Moving average
    # span=period means the "center of mass" covers this many bars
    # adjust=False uses the recursive formula (standard in trading)
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index (RSI)
    ------------------------------
    Measures how "overbought" or "oversold" a stock is, on a scale of 0 to 100.

    How to read it:
    - RSI > 70 → Overbought (stock might be too expensive, could drop)
    - RSI < 30 → Oversold (stock might be too cheap, could bounce)
    - RSI 40-60 → Neutral

    How it works (step by step):
    1. Look at price changes between consecutive bars
    2. Separate the UP moves (gains) from the DOWN moves (losses)
    3. Average the gains and losses over the lookback period
    4. Ratio = average gain / average loss → this is "Relative Strength"
    5. Convert to a 0-100 scale

    Args:
        series: Closing prices
        period: Lookback period (14 is the standard used by most traders)

    Returns:
        RSI values (0-100) for each price point
    """
    # Step 1: Calculate price change at each bar
    # diff() subtracts the previous value → positive = price went up
    delta = series.diff()

    # Step 2: Separate gains from losses
    # .where(condition, 0) → keep value if condition is True, else replace with 0
    gain = delta.where(delta > 0, 0.0)     # Keep only positive changes
    loss = -delta.where(delta < 0, 0.0)    # Keep only negative changes (make them positive)

    # Step 3: Calculate the exponential moving average of gains and losses
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    # Step 4: Calculate Relative Strength
    rs = avg_gain / avg_loss

    # Step 5: Convert to 0-100 scale
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
):
    """
    Moving Average Convergence Divergence (MACD)
    ----------------------------------------------
    Shows the relationship between two moving averages. Used to spot
    changes in trend direction, strength, and momentum.

    Three components:
    1. MACD Line = Fast EMA − Slow EMA
       → When fast EMA is above slow EMA, momentum is bullish
    2. Signal Line = EMA of the MACD Line (a smoothed version)
    3. Histogram = MACD Line − Signal Line
       → Green/growing = bullish momentum increasing
       → Red/shrinking = bearish momentum increasing

    Key trading signals:
    - MACD crosses ABOVE signal → Bullish (potential buy)
    - MACD crosses BELOW signal → Bearish (potential sell)
    - Histogram growing → Momentum is increasing
    - Histogram shrinking → Momentum is fading

    Args:
        series: Closing prices
        fast:   Fast EMA period (default 12)
        slow:   Slow EMA period (default 26)
        signal: Signal line period (default 9)

    Returns:
        Tuple of (macd_line, signal_line, histogram) — each is a pd.Series
    """
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)

    macd_line = ema_fast - ema_slow                # Difference between fast & slow
    signal_line = calculate_ema(macd_line, signal)  # Smoothed version of MACD
    histogram = macd_line - signal_line             # Gap between MACD and signal

    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    series: pd.Series,
    period: int = 20,
    num_std: float = 2.0,
):
    """
    Bollinger Bands
    ----------------
    Three lines forming a "channel" around the stock price:
    - Upper Band = Average + 2 × standard deviation (acts as resistance)
    - Middle Band = Simple Moving Average (reference for the trend)
    - Lower Band = Average − 2 × standard deviation (acts as support)

    KEY CONCEPT — "Bollinger Squeeze":
    When the bands get VERY TIGHT (narrow), the stock is consolidating in
    a small range. This compression often happens RIGHT BEFORE a big move.
    Think of it like a spring being squeezed — the tighter it gets, the
    bigger the snap when it releases.

    The "bandwidth" measures how wide the bands are:
    - Low bandwidth = tight bands = potential breakout coming!
    - High bandwidth = wide bands = stock is already moving a lot

    Args:
        series: Closing prices
        period: Lookback period (default 20 is standard)
        num_std: Number of standard deviations for the bands (default 2)

    Returns:
        Tuple of (upper_band, middle_band, lower_band, bandwidth)
    """
    # Middle band = Simple Moving Average (average of the last N closing prices)
    middle = series.rolling(window=period).mean()

    # Standard deviation = how spread out prices are from the average
    std = series.rolling(window=period).std()

    # Upper and lower bands
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)

    # Bandwidth = how wide the bands are, as a fraction of the middle band
    # Smaller bandwidth = tighter squeeze = bigger potential breakout
    bandwidth = (upper - lower) / middle

    return upper, middle, lower, bandwidth


def calculate_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    """
    Volume Weighted Average Price (VWAP)
    --------------------------------------
    The "fair price" for the day, weighted by volume. If most volume traded
    at $100, VWAP will be near $100 even if the price moved to $110 later.

    How traders use it:
    - Price ABOVE VWAP → Buyers are in control (bullish)
    - Price BELOW VWAP → Sellers are in control (bearish)
    - VWAP itself often acts as support/resistance

    Args:
        high, low, close: Price data columns
        volume: Volume data column

    Returns:
        VWAP values as a Series
    """
    # Typical price = average of High, Low, Close for each bar
    typical_price = (high + low + close) / 3

    # Running total of (price × volume) divided by running total of volume
    cumulative_tp_vol = (typical_price * volume).cumsum()
    cumulative_vol = volume.cumsum()

    return cumulative_tp_vol / cumulative_vol


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """
    Average True Range (ATR)
    -------------------------
    Measures how much a stock typically moves (its volatility).
    Higher ATR = more volatile / bigger price swings.

    "True Range" is smarter than just (high − low) because it also accounts
    for gaps — when a stock opens at a very different price than it closed.

    Used for:
    - Setting stop-loss levels (e.g., 2× ATR below entry)
    - Identifying breakouts (price moves more than usual ATR)

    Args:
        high, low, close: Price data columns
        period: Lookback period (default 14)

    Returns:
        ATR values as a Series
    """
    # True Range is the LARGEST of these three measurements:
    tr1 = high - low                     # Today's range
    tr2 = abs(high - close.shift())      # Gap up from yesterday's close
    tr3 = abs(low - close.shift())       # Gap down from yesterday's close

    # Take the maximum of the three for each bar
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Average it over the period
    return true_range.rolling(window=period).mean()
