"""
Dynamic Stock Discovery Module
================================
Instead of scanning a hardcoded list of stocks, this module discovers
the most active, fastest-moving stocks in REAL TIME from Yahoo Finance.

HOW IT WORKS:
─────────────
1. We run multiple Yahoo Finance "screener" queries to find interesting stocks:
   - Most Active (highest volume today) → catches institutional moves
   - Day Gainers (biggest % gain) → stocks already breaking out
   - Day Losers (biggest % drop) → potential reversal candidates
   - Penny Stocks (under $5 with volume) → catches small-cap movers
2. We merge all the results and remove duplicates.
3. The discovered list is CACHED so we don't query Yahoo's screener
   on every 5-second refresh — only the price data refreshes frequently.

PYTHON CONCEPTS:
────────────────
- "set()" is like a list but automatically removes duplicates.
  set(["AAPL", "TSLA", "AAPL"]) → {"AAPL", "TSLA"}
- "try/except" catches errors so one failed screener doesn't crash everything.
- We import EquityQuery from yfinance to build custom filters — think of it
  like building a search query: "region = US AND volume > 1 million".
"""

import time
import logging
from typing import List

import yfinance as yf
from yfinance.screener import EquityQuery

import config

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE — discovered tickers are cached separately from price data.
# Stock discovery refreshes every DISCOVERY_CACHE_DURATION seconds (default 5 min).
# Price data refreshes every CACHE_DURATION seconds (default 30s).
# ═══════════════════════════════════════════════════════════════════════════════

_discovery_cache = {
    "tickers": [],
    "timestamp": 0,
}


def _is_discovery_cache_valid() -> bool:
    """Check if the discovered stock list is still fresh."""
    age = time.time() - _discovery_cache["timestamp"]
    return age < config.DISCOVERY_CACHE_DURATION and len(_discovery_cache["tickers"]) > 0


def clear_discovery_cache():
    """Force a fresh stock discovery on the next request."""
    _discovery_cache["tickers"] = []
    _discovery_cache["timestamp"] = 0


# ═══════════════════════════════════════════════════════════════════════════════
# SCREENER QUERIES — each function fetches a different "type" of interesting stock
# ═══════════════════════════════════════════════════════════════════════════════

def _screen_most_active(count: int) -> List[str]:
    """
    Find the most actively traded US stocks (sorted by volume).

    Why this matters:
    High volume = lots of traders are interested → bigger moves → better signals.
    This query has NO price floor, so it catches everything from $0.01 penny
    stocks to $500+ blue chips.
    """
    try:
        query = EquityQuery("AND", [
            EquityQuery("EQ", ["region", "us"]),
            EquityQuery("GT", ["dayvolume", config.DISCOVERY_MIN_VOLUME]),
        ])
        result = yf.screen(query, sortField="dayvolume", sortAsc=False, count=count)
        quotes = result.get("quotes", [])
        tickers = [q["symbol"] for q in quotes if "symbol" in q]
        logger.info(f"Most Active: found {len(tickers)} stocks (of {result.get('total', '?')} total)")
        return tickers
    except Exception as e:
        logger.error(f"Most Active screener failed: {e}")
        return []


def _screen_gainers(count: int) -> List[str]:
    """
    Find stocks with the biggest % gains today.

    Why this matters:
    Stocks already moving up strongly may continue (momentum) or may be
    setting up for a reversal if they've gone too far too fast.
    """
    try:
        query = EquityQuery("AND", [
            EquityQuery("EQ", ["region", "us"]),
            EquityQuery("GT", ["percentchange", config.DISCOVERY_MIN_CHANGE_PCT]),
            EquityQuery("GT", ["dayvolume", config.DISCOVERY_MIN_VOLUME]),
        ])
        result = yf.screen(query, sortField="percentchange", sortAsc=False, count=count)
        quotes = result.get("quotes", [])
        tickers = [q["symbol"] for q in quotes if "symbol" in q]
        logger.info(f"Day Gainers: found {len(tickers)} stocks")
        return tickers
    except Exception as e:
        logger.error(f"Day Gainers screener failed: {e}")
        return []


def _screen_losers(count: int) -> List[str]:
    """
    Find stocks with the biggest % losses today.

    Why this matters:
    Stocks that dropped significantly may be oversold → bullish reversal candidates.
    A stock falling on high volume can also signal a bearish breakdown.
    """
    try:
        query = EquityQuery("AND", [
            EquityQuery("EQ", ["region", "us"]),
            EquityQuery("LT", ["percentchange", -config.DISCOVERY_MIN_CHANGE_PCT]),
            EquityQuery("GT", ["dayvolume", config.DISCOVERY_MIN_VOLUME]),
        ])
        result = yf.screen(query, sortField="percentchange", sortAsc=True, count=count)
        quotes = result.get("quotes", [])
        tickers = [q["symbol"] for q in quotes if "symbol" in q]
        logger.info(f"Day Losers: found {len(tickers)} stocks")
        return tickers
    except Exception as e:
        logger.error(f"Day Losers screener failed: {e}")
        return []


def _screen_penny_stocks(count: int) -> List[str]:
    """
    Find penny stocks (under $5) with significant trading volume.

    Why this matters:
    Penny stocks can make huge % moves in minutes. They're volatile and
    risky, but often show clear breakout patterns because they trade in
    well-defined channels.
    """
    try:
        query = EquityQuery("AND", [
            EquityQuery("EQ", ["region", "us"]),
            EquityQuery("LT", ["intradayprice", config.DISCOVERY_PENNY_MAX_PRICE]),
            EquityQuery("GT", ["intradayprice", 0.001]),  # Exclude zero-price
            EquityQuery("GT", ["dayvolume", config.DISCOVERY_PENNY_MIN_VOLUME]),
        ])
        result = yf.screen(query, sortField="dayvolume", sortAsc=False, count=count)
        quotes = result.get("quotes", [])
        tickers = [q["symbol"] for q in quotes if "symbol" in q]
        logger.info(f"Penny Stocks: found {len(tickers)} stocks (of {result.get('total', '?')} total)")
        return tickers
    except Exception as e:
        logger.error(f"Penny Stocks screener failed: {e}")
        return []


def _screen_volatile(count: int) -> List[str]:
    """
    Find stocks with big intraday price swings (either direction).

    Why this matters:
    Volatile stocks = more trading opportunities. If a stock barely moves,
    there's nothing to trade. We want stocks that are MOVING.
    """
    try:
        # Gainers side
        q_up = EquityQuery("AND", [
            EquityQuery("EQ", ["region", "us"]),
            EquityQuery("GT", ["percentchange", 5]),
            EquityQuery("GT", ["dayvolume", config.DISCOVERY_MIN_VOLUME]),
        ])
        r_up = yf.screen(q_up, sortField="dayvolume", sortAsc=False, count=count // 2)
        tickers_up = [q["symbol"] for q in r_up.get("quotes", []) if "symbol" in q]

        # Losers side
        q_down = EquityQuery("AND", [
            EquityQuery("EQ", ["region", "us"]),
            EquityQuery("LT", ["percentchange", -5]),
            EquityQuery("GT", ["dayvolume", config.DISCOVERY_MIN_VOLUME]),
        ])
        r_down = yf.screen(q_down, sortField="dayvolume", sortAsc=False, count=count // 2)
        tickers_down = [q["symbol"] for q in r_down.get("quotes", []) if "symbol" in q]

        combined = tickers_up + tickers_down
        logger.info(f"Volatile: found {len(combined)} stocks")
        return combined
    except Exception as e:
        logger.error(f"Volatile screener failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DISCOVERY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def discover_stocks(force_refresh: bool = False) -> List[str]:
    """
    Main entry point — discovers actively trading US stocks in real time.

    How it works:
    1. Runs each enabled screener query (most active, gainers, losers, penny stocks)
    2. Merges all results into one list, removing duplicates
    3. Limits to DISCOVERY_MAX_STOCKS total (to keep API calls manageable)
    4. Caches for DISCOVERY_CACHE_DURATION seconds (default 5 minutes)

    The frontend polls every 5s for PRICE data, but the stock LIST itself
    only updates every 5 minutes. This prevents excessive Yahoo API calls.

    Args:
        force_refresh: If True, bypass the cache and discover fresh stocks

    Returns:
        List of ticker symbols, e.g., ["NVDA", "PLUG", "AMC", "TSLA", ...]
    """
    # Return cached list if it's still fresh
    if not force_refresh and _is_discovery_cache_valid():
        return _discovery_cache["tickers"]

    logger.info("Discovering stocks from live market data...")
    start = time.time()

    # ── Collect tickers from each screener ──
    # Using a set automatically removes duplicates
    all_tickers = set()

    # How many stocks to fetch per screener
    per_screen = config.DISCOVERY_PER_SCREEN

    # Map screener names to their functions
    screener_map = {
        "most_active": _screen_most_active,
        "gainers": _screen_gainers,
        "losers": _screen_losers,
        "penny_stocks": _screen_penny_stocks,
        "volatile": _screen_volatile,
    }

    # Run each enabled screener
    for name in config.DISCOVERY_SCREENS:
        if name in screener_map:
            tickers = screener_map[name](per_screen)
            all_tickers.update(tickers)
        else:
            logger.warning(f"Unknown screener: '{name}'. Available: {list(screener_map.keys())}")

    # Convert set to sorted list and limit total count
    # Filter out non-standard symbols (hyphens, digits, etc.) that providers
    # like Alpaca reject — e.g., "BUI-RI" (rights), "AAPL240119C..." (options)
    import re
    valid_ticker = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")
    final_tickers = sorted(t for t in all_tickers if valid_ticker.match(t))
    final_tickers = final_tickers[:config.DISCOVERY_MAX_STOCKS]

    elapsed = round(time.time() - start, 1)
    logger.info(
        f"Discovery complete: {len(final_tickers)} unique stocks "
        f"from {len(config.DISCOVERY_SCREENS)} screeners in {elapsed}s"
    )

    # Cache the result
    _discovery_cache["tickers"] = final_tickers
    _discovery_cache["timestamp"] = time.time()

    return final_tickers
