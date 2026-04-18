"""
Data Provider Module
=====================
Fetches intraday market data from Yahoo Finance, Alpaca Markets, or Polygon.io.

How it works:
─────────────
1. Stocks to scan are discovered dynamically via stock_discovery.discover_stocks()
   (no hardcoded ticker list — includes penny stocks, high-volume movers, etc.)
2. The main function fetch_stock_data() downloads price data (Open, High, Low,
   Close, Volume) for all discovered stocks.
3. Results are cached in memory so we don't hit the API on every request.
4. The cache expires after CACHE_DURATION seconds (set in config.py).
5. Call with force_refresh=True to bypass the cache (e.g., when user clicks Refresh).

PYTHON CONCEPTS USED:
─────────────────────
- "dict" (dictionary) maps keys to values, like {"AAPL": <price data>}
- "try/except" catches errors so one bad stock doesn't crash the whole scan
- time.time() returns the current time in seconds — used for cache timing
"""

import time
import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

import config
from stock_discovery import discover_stocks, clear_discovery_cache

# Logger prints messages to the console so you can see what's happening
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE — stores downloaded data in memory to avoid re-fetching too often
# ═══════════════════════════════════════════════════════════════════════════════

_cache = {
    "1m": {"data": {}, "timestamp": 0},
    "5m": {"data": {}, "timestamp": 0},
    "10m": {"data": {}, "timestamp": 0},
}


def is_cache_valid(timeframe: str) -> bool:
    """
    Check if cached data is still fresh.
    Returns True if the data was fetched less than CACHE_DURATION seconds ago.
    """
    age = time.time() - _cache[timeframe]["timestamp"]
    return age < config.CACHE_DURATION


def get_cached_data(timeframe: str) -> dict:
    """Return the cached data dictionary for a given timeframe."""
    return _cache[timeframe]["data"]


def set_cache(timeframe: str, data: dict):
    """Store data in cache and record the current time."""
    _cache[timeframe]["data"] = data
    _cache[timeframe]["timestamp"] = time.time()


def clear_cache():
    """
    Clear ALL cached data (both price data and discovered stock list).
    Called when the user clicks "Refresh" or changes config settings.
    """
    for tf in _cache:
        _cache[tf]["data"] = {}
        _cache[tf]["timestamp"] = 0
    clear_discovery_cache()


# ═══════════════════════════════════════════════════════════════════════════════
# YAHOO FINANCE PROVIDER (free, no API key needed)
# ═══════════════════════════════════════════════════════════════════════════════

def _resample_to_10m(df: pd.DataFrame) -> pd.DataFrame:
    """Resample 5-minute OHLCV bars into 10-minute bars."""
    return df.resample("10min").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }).dropna(how="all")


def _fetch_yfinance(tickers: list, interval: str) -> dict:
    """
    Fetch stock data from Yahoo Finance.

    How it works:
    1. We call yf.download() with ALL tickers at once (much faster than one-by-one).
    2. yfinance returns a big table where columns are grouped by stock.
    3. We split it into individual DataFrames — one per stock.

    Limitations:
    - 1-minute data: only available for the last 7 days (we fetch 1 day)
    - 5-minute data: available for the last 60 days (we fetch 5 days)
    - Data may have a ~15 minute delay outside of market hours

    Args:
        tickers: List of stock symbols, e.g., ["AAPL", "MSFT", "TSLA"]
        interval: Time between candles — "1m" (1 minute) or "5m" (5 minutes)

    Returns:
        Dictionary mapping each ticker to its DataFrame of OHLCV data.
        Example: {"AAPL": DataFrame(Open, High, Low, Close, Volume), ...}
    """
    # How far back to look depends on the candle size
    period_map = {"1m": "1d", "5m": "5d", "10m": "5d"}
    period = period_map.get(interval, "5d")

    # yfinance doesn't support 10m directly; use 5m and resample
    yf_interval = "5m" if interval == "10m" else interval

    result = {}

    try:
        logger.info(f"Downloading {interval} data for {len(tickers)} stocks from Yahoo Finance...")

        # Download ALL tickers in one request (yfinance batches them internally)
        # group_by="ticker" → organises columns by stock symbol
        # progress=False → don't print a progress bar to the console
        # threads=True → use multiple threads for speed
        data = yf.download(
            tickers=tickers,
            period=period,
            interval=yf_interval,
            group_by="ticker",
            progress=False,
            threads=True,
            prepost=True,
        )

        if data.empty:
            logger.warning("Yahoo Finance returned no data (market may be closed)")
            return result

        # ── Handle single-ticker edge case ──
        # When only 1 ticker is requested, yfinance returns a flat DataFrame
        # instead of a multi-level one, so we handle it separately.
        if len(tickers) == 1:
            ticker = tickers[0]
            if not data.empty and len(data) > 10:
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.droplevel(1)
                if interval == "10m":
                    data = _resample_to_10m(data)
                result[ticker] = data
        else:
            # ── Multiple tickers: extract each one ──
            for ticker in tickers:
                try:
                    ticker_data = data[ticker].copy()

                    # Drop rows where all values are NaN (no data for this ticker)
                    ticker_data = ticker_data.dropna(how="all")

                    # We need at least 10 bars for meaningful technical analysis
                    if len(ticker_data) > 10:
                        if interval == "10m":
                            ticker_data = _resample_to_10m(ticker_data)
                        if len(ticker_data) > 10:
                            result[ticker] = ticker_data
                except (KeyError, Exception) as e:
                    # Some tickers may not have data — skip them silently
                    logger.debug(f"No data for {ticker}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Error fetching from Yahoo Finance: {e}")

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# ALPACA PROVIDER (free real-time data, requires account signup)
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_alpaca(tickers: list, interval: str) -> dict:
    """
    Fetch stock data from Alpaca Markets (real-time, free tier available).

    To set up:
    1. Create a free account at https://alpaca.markets
    2. Generate API keys in your dashboard
    3. Paste them in config.py (ALPACA_API_KEY and ALPACA_SECRET_KEY)
    4. Change DATA_PROVIDER to "alpaca" in config.py

    Args:
        tickers: List of stock symbols
        interval: "1m" or "5m"

    Returns:
        Same format as _fetch_yfinance: {ticker: DataFrame, ...}
    """
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
        from alpaca.data.enums import DataFeed
    except ImportError:
        logger.error(
            "Alpaca SDK not installed! Run: pip install alpaca-py\n"
            "Or switch to yfinance in config.py: DATA_PROVIDER = 'yfinance'"
        )
        return {}

    if not config.ALPACA_API_KEY or not config.ALPACA_SECRET_KEY:
        logger.error("Alpaca API keys not set in config.py")
        return {}

    client = StockHistoricalDataClient(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY)

    # Map our interval strings to Alpaca's TimeFrame objects
    interval_map = {
        "1m": TimeFrame.Minute,
        "5m": TimeFrame(5, TimeFrameUnit.Minute),
        "10m": TimeFrame(10, TimeFrameUnit.Minute),
    }
    tf = interval_map.get(interval, TimeFrame(5, TimeFrameUnit.Minute))

    end = datetime.now()
    start = end - timedelta(days=5 if interval == "1m" else 10)

    result = {}

    try:
        # Feed selection (configurable in config.py → ALPACA_DATA_FEED):
        #   IEX  → free, limited extended-hours (only IEX exchange trades)
        #   SIP  → paid, full pre-market (4 AM ET) + after-hours (8 PM ET)
        feed_choice = getattr(config, "ALPACA_DATA_FEED", "iex").upper()
        feed = DataFeed.SIP if feed_choice == "SIP" else DataFeed.IEX
        request = StockBarsRequest(
            symbol_or_symbols=tickers,
            timeframe=tf,
            start=start,
            end=end,
            feed=feed,
        )
        bars = client.get_stock_bars(request)

        for ticker in tickers:
            try:
                ticker_bars = bars[ticker]
                if ticker_bars:
                    df = pd.DataFrame([{
                        "Open": bar.open,
                        "High": bar.high,
                        "Low": bar.low,
                        "Close": bar.close,
                        "Volume": bar.volume,
                    } for bar in ticker_bars])
                    df.index = [bar.timestamp for bar in ticker_bars]
                    if len(df) > 10:
                        result[ticker] = df
            except (KeyError, Exception):
                continue

        logger.info(f"Alpaca returned data for {len(result)} stocks ({feed_choice} feed, includes extended hours)")
    except Exception as e:
        logger.error(f"Error fetching from Alpaca: {e}")

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# POLYGON.IO PROVIDER (free tier has extended hours; paid tier is real-time)
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_polygon(tickers: list, interval: str) -> dict:
    """
    Fetch stock data from Polygon.io (now Massive.com).

    Key advantages:
    - Free tier includes pre-market + after-hours data (delayed by 15 min)
    - Paid tier ($29/mo) gives real-time data with full extended hours

    Limitation:
    - Free tier: 5 API calls/minute. Each ticker = 1 call.
      If you have >30 stocks, some may be skipped due to rate limits.
      Reduce DISCOVERY_MAX_STOCKS in config.py or upgrade your plan.

    To set up:
    1. Sign up at https://polygon.io (redirects to https://massive.com)
    2. Go to Dashboard → API Keys → copy your key
    3. Paste it in config.py (POLYGON_API_KEY)
    4. Set DATA_PROVIDER = "polygon" in config.py

    Args:
        tickers: List of stock symbols
        interval: "1m" or "5m"

    Returns:
        Same format as other providers: {ticker: DataFrame, ...}
    """
    try:
        from polygon import RESTClient
    except ImportError:
        logger.error(
            "Polygon SDK not installed! Run: pip install polygon-api-client\n"
            "Or switch to yfinance in config.py: DATA_PROVIDER = 'yfinance'"
        )
        return {}

    api_key = getattr(config, "POLYGON_API_KEY", "")
    if not api_key:
        logger.error("Polygon API key not set in config.py (POLYGON_API_KEY)")
        return {}

    client = RESTClient(api_key=api_key)

    # Map interval to Polygon's multiplier + timespan
    multiplier = {"1m": 1, "5m": 5, "10m": 10}.get(interval, 5)
    timespan = "minute"

    end = datetime.now()
    start = end - timedelta(days=5 if interval == "1m" else 10)

    from_date = start.strftime("%Y-%m-%d")
    to_date = end.strftime("%Y-%m-%d")

    result = {}
    fetched = 0

    logger.info(f"Fetching {interval} data for {len(tickers)} stocks from Polygon.io...")

    for ticker in tickers:
        try:
            aggs = list(client.list_aggs(
                ticker=ticker,
                multiplier=multiplier,
                timespan=timespan,
                from_=from_date,
                to=to_date,
                limit=50000,
            ))

            if aggs and len(aggs) > 10:
                df = pd.DataFrame([{
                    "Open": a.open,
                    "High": a.high,
                    "Low": a.low,
                    "Close": a.close,
                    "Volume": a.volume,
                } for a in aggs])
                # Polygon timestamps are in milliseconds
                df.index = pd.to_datetime([a.timestamp for a in aggs], unit="ms")
                result[ticker] = df
                fetched += 1

        except Exception as e:
            err_str = str(e).lower()
            if "rate" in err_str or "429" in err_str:
                # Hit rate limit — pause and continue with what we have
                logger.warning(
                    f"Polygon rate limit hit after {fetched} stocks. "
                    f"Free tier allows 5 calls/min. Returning partial results. "
                    f"Reduce DISCOVERY_MAX_STOCKS or upgrade your Polygon plan."
                )
                break
            logger.debug(f"No Polygon data for {ticker}: {e}")
            continue

    logger.info(f"Polygon returned data for {len(result)} stocks (includes extended hours)")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN FETCH FUNCTION (call this from the scanner)
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_stock_data(timeframe: str = "1m", force_refresh: bool = False) -> dict:
    """
    Main entry point — fetches stock data using the configured provider.

    Two-layer caching:
    1. Stock DISCOVERY is cached for ~5 minutes (which tickers to scan)
    2. Price DATA is cached for ~30 seconds (OHLCV candles)

    This means the frontend can poll every 5 seconds without triggering
    excessive API calls.

    Args:
        timeframe:     "1m" for 1-minute candles, "5m" for 5-minute candles
        force_refresh: If True, ignore cache and fetch fresh data

    Returns:
        Dictionary mapping ticker → DataFrame of OHLCV data
        Example: {
            "AAPL": DataFrame(Open, High, Low, Close, Volume),
            "MSFT": DataFrame(Open, High, Low, Close, Volume),
        }
    """
    # Return cached data if it's still fresh
    if not force_refresh and is_cache_valid(timeframe):
        logger.info(f"Using cached {timeframe} data ({len(get_cached_data(timeframe))} stocks)")
        return get_cached_data(timeframe)

    # Step 1: Discover which stocks to scan (cached separately, refreshes every ~5 min)
    tickers = discover_stocks(force_refresh=force_refresh)

    if not tickers:
        logger.warning("No stocks discovered — market may be closed or screener failed")
        return {}

    logger.info(f"Fetching fresh {timeframe} data for {len(tickers)} discovered stocks...")

    # Step 2: Download price data for all discovered stocks
    if config.DATA_PROVIDER == "alpaca":
        data = _fetch_alpaca(tickers, timeframe)
    elif config.DATA_PROVIDER == "polygon":
        data = _fetch_polygon(tickers, timeframe)
    else:
        data = _fetch_yfinance(tickers, timeframe)

    # Store in cache for next time
    if data:
        set_cache(timeframe, data)
        logger.info(f"Cached {timeframe} data for {len(data)} stocks")

    return data
