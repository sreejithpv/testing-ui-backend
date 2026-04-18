"""
Configuration File for My Trading Helper
==========================================
Edit the values below to customize how the scanner works.
All settings can also be updated at runtime via the /api/config endpoint.

HOW TO USE:
- Change any value below and restart the backend, OR
- Use the config panel in the UI to change settings without restarting

SECRET MANAGEMENT:
- Sensitive credentials (API keys) are loaded from environment variables
- Copy .env.example to .env and fill in your actual credentials
- NEVER commit .env to version control
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
load_dotenv()

# ─── DATA PROVIDER ─────────────────────────────────────────────────────────────
# Which service to pull stock data from:
#   "yfinance" → Free, no signup needed. Great for development.
#                Has ~15-min delay but often provides near-real-time during market hours.
#   "alpaca"   → Free real-time data. Requires a free account at https://alpaca.markets
#   "polygon"  → Free tier: delayed data w/ extended hours (5 calls/min, best for <30 stocks).
#                Paid ($29/mo): unlimited calls, real-time, full pre/post market.
#                Sign up at https://polygon.io (now Massive.com)
DATA_PROVIDER = "alpaca"

# Alpaca API credentials (only needed if DATA_PROVIDER = "alpaca")
# 1. Sign up free at https://alpaca.markets
# 2. Go to Paper Trading → API Keys → Generate
# 3. Set environment variables ALPACA_API_KEY and ALPACA_SECRET_KEY
#    or add them to .env file (copy from .env.example)
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

# Alpaca data feed:
#   "iex"  → Free. Limited pre-market / after-hours coverage (only IEX exchange trades).
#   "sip"  → Paid ($9/mo or included with live trading). Full pre-market (4 AM ET)
#            and after-hours (until 8 PM ET) data from all US exchanges.
# If you don't see extended-hours data, switch to "sip" (requires a paid data subscription).
ALPACA_DATA_FEED = "iex"

# Polygon.io (Massive) API key (only needed if DATA_PROVIDER = "polygon")
# 1. Sign up free at https://polygon.io (now https://massive.com)
# 2. Set environment variable POLYGON_API_KEY or add to .env file
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")below
POLYGON_API_KEY = ""

# ─── STOCK DISCOVERY (DYNAMIC) ────────────────────────────────────────────────
# Instead of a hardcoded list, stocks are discovered in real time from Yahoo
# Finance screeners. This catches penny stocks, trending stocks, and any ticker
# that's actively moving — no manual updates needed.
#
# Which screeners to run (see stock_discovery.py for details):
#   "most_active"   → Highest volume today (catches institutional interest)
#   "gainers"       → Biggest % gains (momentum / breakout candidates)
#   "losers"        → Biggest % drops (reversal candidates)
#   "penny_stocks"  → Under $5 with volume (small-cap movers)
#   "volatile"      → Big swings either direction (active traders)
DISCOVERY_SCREENS = ["most_active", "gainers", "losers", "penny_stocks", "volatile"]

# How many stocks to fetch per screener query (more = wider coverage, slower scan)
DISCOVERY_PER_SCREEN = 50

# Maximum total stocks to scan after merging all screeners
# Higher = more coverage but slower. 200 is a good balance.
DISCOVERY_MAX_STOCKS = 200

# How often to re-discover stocks (seconds). Stock PRICES refresh every
# CACHE_DURATION seconds, but the stock LIST refreshes at this slower interval.
# 300 = 5 minutes. No need to rediscover more often than this.
DISCOVERY_CACHE_DURATION = 300

# Minimum daily volume for a stock to be included (filters out illiquid junk)
DISCOVERY_MIN_VOLUME = 500000

# Minimum absolute % change for gainers/losers screeners
DISCOVERY_MIN_CHANGE_PCT = 3

# Penny stock price ceiling (stocks below this price are "penny stocks")
DISCOVERY_PENNY_MAX_PRICE = 5

# Minimum volume for penny stocks (lower bar since they trade less)
DISCOVERY_PENNY_MIN_VOLUME = 200000

# ─── SCANNER SETTINGS ─────────────────────────────────────────────────────────
MAX_RESULTS = 20            # Maximum number of stocks to return per category
CACHE_DURATION = 30         # Seconds to keep cached data before re-fetching from API

# ─── TIMEFRAMES ────────────────────────────────────────────────────────────────
# Which candle sizes to analyze
TIMEFRAMES = ["1m", "5m", "10m"]

# ─── SORTING ───────────────────────────────────────────────────────────────────
# How to sort the results. Options: "pct_change", "score", "volume"
SORT_BY = "pct_change"
# Sort direction: "desc" (highest first) or "asc" (lowest first)
SORT_ORDER = "desc"

# ─── BREAKOUT DETECTION THRESHOLDS ────────────────────────────────────────────
# Bollinger Band bandwidth below this value = "squeeze" (tight range, breakout likely)
# Lower = tighter squeeze = stronger signal. Typical range: 0.02 to 0.06
BB_SQUEEZE_THRESHOLD = 0.04

# Volume must be at least this many times the 20-bar average to count as a "surge"
# 1.5 = 50% above average. Increase for stricter filtering.
VOLUME_SURGE_MULTIPLIER = 1.5

# RSI range that indicates "building momentum" (not yet overbought)
RSI_MOMENTUM_LOW = 45
RSI_MOMENTUM_HIGH = 65

# ─── TREND REVERSAL THRESHOLDS ────────────────────────────────────────────────
# Minimum volume on the current bar for a stock to be included in results.
# Filters out illiquid/low-volume tickers. 10000 is a good floor.
MIN_VOLUME = 10000

# RSI below this = oversold (potential bullish reversal)
RSI_OVERSOLD = 30
# RSI above this = overbought (potential bearish reversal)
RSI_OVERBOUGHT = 70
