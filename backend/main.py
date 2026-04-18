"""
My Trading Helper — Backend API Server
========================================
A FastAPI server that scans US stocks for breakout candidates and trend reversals.

HOW TO RUN:
    cd backend
    pip install -r requirements.txt
    python main.py

    Server starts at → http://localhost:8000

API ENDPOINTS:
    GET  /api/scan            → Get breakout and reversal stocks
    GET  /api/scan?force=1    → Force refresh (bypass cache)
    GET  /api/scan?timeframe=5m → Scan using 5-minute candles
    GET  /api/config          → Get current configuration
    POST /api/config          → Update configuration at runtime
    POST /api/refresh         → Clear cache
    GET  /api/health          → Health check

PYTHON CONCEPTS:
    - "async def" → an asynchronous function that can handle multiple requests
      at once without blocking. FastAPI uses this for better performance.
    - "@app.get('/path')" → a "decorator" that tells FastAPI to call this
      function when someone visits that URL path.
    - "Query(...)" → tells FastAPI about URL parameters like ?timeframe=5m
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config
from data_provider import fetch_stock_data, clear_cache
from scanner import scan_stocks
from stock_discovery import discover_stocks, clear_discovery_cache

# ── Set up logging ──
# This prints timestamped messages to your terminal so you can see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# APP SETUP
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs when the server starts and stops.
    Good place to log startup info or initialize resources.
    """
    logger.info("My Trading Helper backend starting...")
    logger.info(f"Dynamic stock discovery enabled — scanning live market movers via {config.DATA_PROVIDER}")
    logger.info(f"Screeners: {config.DISCOVERY_SCREENS}")
    yield
    logger.info("Backend shutting down...")


# Create the FastAPI application
app = FastAPI(
    title="My Trading Helper",
    description="Intraday stock breakout & trend reversal scanner",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS Middleware ──
# "CORS" = Cross-Origin Resource Sharing
# The frontend (port 5173) and backend (port 8000) run on different ports.
# Without CORS, the browser would block the frontend from calling the backend API.
# This middleware tells the browser: "It's OK, allow requests from any origin."
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/scan")
async def scan(
    timeframe: str = Query("1m", description="Candle timeframe: '1m' or '5m'"),
    force: bool = Query(False, description="Force refresh — ignore cached data"),
    sort_by: str = Query(None, description="Sort by: 'pct_change', 'score', 'volume'"),
    sort_order: str = Query(None, description="Sort direction: 'asc' or 'desc'"),
    max_results: int = Query(None, description="Max stocks per category"),
):
    """
    MAIN ENDPOINT — Scan stocks for breakout candidates and trend reversals.

    Returns two lists:
    - breakouts: Stocks showing signs of an imminent breakout
    - reversals: Stocks showing signs of a trend change (bullish or bearish)

    Plus metadata about the scan (how many stocks scanned, how long it took, etc.)
    """
    try:
        start_time = time.time()

        # Step 1: Fetch market data (uses cache unless force=True)
        stock_data = fetch_stock_data(timeframe=timeframe, force_refresh=force)

        if not stock_data:
            return {
                "breakouts": [],
                "reversals": [],
                "meta": {
                    "total_scanned": 0,
                    "timeframe": timeframe,
                    "message": "No data available. Market may be closed or API may be down.",
                    "scan_time": 0,
                },
            }

        # Step 2: Run the scanner (analyze + score + sort + filter)
        results = scan_stocks(
            stock_data,
            sort_by=sort_by,
            sort_order=sort_order,
            max_results=max_results,
        )

        elapsed = round(time.time() - start_time, 2)

        # Step 3: Add metadata so the frontend knows what happened
        results["meta"] = {
            "total_scanned": len(stock_data),
            "breakout_count": len(results["breakouts"]),
            "breakdown_count": len(results["breakdowns"]),
            "reversal_count": len(results["reversals"]),
            "timeframe": timeframe,
            "scan_time": elapsed,
            "cached": not force and elapsed < 1,
        }

        return results

    except Exception as e:
        logger.error(f"Scan error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.get("/api/config")
async def get_config():
    """Return the current scanner configuration so the frontend can display it."""
    return {
        "data_provider": config.DATA_PROVIDER,
        "discovery_screens": config.DISCOVERY_SCREENS,
        "discovery_max_stocks": config.DISCOVERY_MAX_STOCKS,
        "discovery_cache_duration": config.DISCOVERY_CACHE_DURATION,
        "max_results": config.MAX_RESULTS,
        "cache_duration": config.CACHE_DURATION,
        "timeframes": config.TIMEFRAMES,
        "sort_by": config.SORT_BY,
        "sort_order": config.SORT_ORDER,
        "bb_squeeze_threshold": config.BB_SQUEEZE_THRESHOLD,
        "volume_surge_multiplier": config.VOLUME_SURGE_MULTIPLIER,
        "rsi_momentum_range": [config.RSI_MOMENTUM_LOW, config.RSI_MOMENTUM_HIGH],
        "rsi_oversold": config.RSI_OVERSOLD,
        "rsi_overbought": config.RSI_OVERBOUGHT,
    }


@app.post("/api/config")
async def update_config(updates: dict):
    """
    Update scanner settings without restarting the server.

    Send a JSON body with the fields you want to change:
    {
        "max_results": 30,
        "sort_by": "score",
        "sort_order": "desc"
    }

    Only whitelisted fields can be updated (for safety).
    """
    # Only these fields can be changed at runtime
    allowed_fields = {
        "max_results": (int,),
        "cache_duration": (int,),
        "sort_by": (str,),
        "sort_order": (str,),
        "bb_squeeze_threshold": (int, float),
        "volume_surge_multiplier": (int, float),
        "rsi_oversold": (int, float),
        "rsi_overbought": (int, float),
    }

    updated = {}
    for key, value in updates.items():
        if key in allowed_fields:
            expected_types = allowed_fields[key]
            if isinstance(value, expected_types):
                # setattr() sets a variable on the config module
                # e.g., setattr(config, "MAX_RESULTS", 30) is like config.MAX_RESULTS = 30
                setattr(config, key.upper(), value)
                updated[key] = value
            else:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Invalid type for '{key}': expected {expected_types}"},
                )

    # Clear cache so the next scan uses the new settings
    clear_cache()

    return {"updated": updated, "message": "Configuration updated. Cache cleared."}


@app.post("/api/refresh")
async def force_refresh():
    """Clear the data cache. The next scan request will fetch fresh data."""
    clear_cache()
    return {"message": "Cache cleared. Next scan will fetch fresh data."}


@app.get("/api/health")
async def health():
    """Simple health check — useful for monitoring or testing if the server is up."""
    return {
        "status": "ok",
        "discovery_screens": config.DISCOVERY_SCREENS,
        "provider": config.DATA_PROVIDER,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RUN THE SERVER
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    # Start the web server on port 8000
    # host="0.0.0.0" → accessible from other devices on your network
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
