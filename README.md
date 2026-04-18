# My Trading Helper 📈

Intraday stock scanner that identifies **breakout candidates** and **trend reversals** across top US stocks using technical analysis on 1-minute and 5-minute charts.

## What It Does

| Column | Description |
|--------|-------------|
| **Breakout Candidates** | Stocks showing tight consolidation (Bollinger Band squeeze), rising volume, and building momentum — a breakout is likely imminent |
| **Trend Reversals** | Stocks changing direction — bullish reversals (was falling, now turning up) and bearish reversals (was rising, now turning down) |

Data refreshes every 5 seconds (configurable). Results are sorted by % price change by default.

---

## Data Source Comparison

| Provider | Price | Real-Time? | Rate Limits | Best For |
|----------|-------|------------|-------------|----------|
| **Yahoo Finance** ✅ | Free | ~15min delay* | Unofficial | Dev/testing — no signup needed |
| **Alpaca Markets** | Free | Yes, real-time | Generous | Production — free account required |
| **Polygon.io** | $29/mo | Yes | Varies by plan | Professional data |
| **Twelve Data** | Free tier | Yes | 800 calls/day | Moderate usage |
| **Alpha Vantage** | Free tier | Delayed | 5 calls/min | Lightweight usage |

\* Yahoo Finance often provides near-real-time data during market hours despite the official 15-min delay.

**Default: Yahoo Finance** (works immediately, no signup). Switch to Alpaca when ready for real-time data.

---

## Quick Start

### Prerequisites

- **Python 3.10+** → [python.org](https://www.python.org/downloads/)
- **Node.js 18+** → [nodejs.org](https://nodejs.org/)

### 1. Start the Backend

```bash
cd backend

# Create a virtual environment (keeps packages isolated from your system)
python3 -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt

# Start the server
python main.py
```

Backend runs at → **http://localhost:8000**

### 2. Start the Frontend

Open a **new terminal**:

```bash
cd frontend

# Install JavaScript packages
npm install

# Start the dev server
npm run dev
```

Frontend runs at → **http://localhost:5173**

### 3. Open the App

Visit **http://localhost:5173** in your browser. Both servers must be running.

---

## Switching to Alpaca (Real-Time Data)

1. Create a free account at [alpaca.markets](https://alpaca.markets)
2. Generate API keys in the dashboard → Paper Trading → API Keys
3. Edit `backend/config.py`:

```python
DATA_PROVIDER = "alpaca"
ALPACA_API_KEY = "your-key-here"
ALPACA_SECRET_KEY = "your-secret-here"
```

4. Install the Alpaca SDK:

```bash
pip install alpaca-py
```

5. Restart the backend

---

## Configuration

### From the UI

Click **⚙️ Settings** in the header to change:
- Max results per column
- Sort field (% change, score, volume)
- Sort order (ascending/descending)
- Auto-refresh interval (3s – 60s)
- Timeframe toggle (1m / 5m)

### From `backend/config.py`

For deeper customization:

```python
# Add/remove stocks to scan
STOCK_UNIVERSE = ["AAPL", "MSFT", ...]

# Adjust breakout detection sensitivity
BB_SQUEEZE_THRESHOLD = 0.04       # Lower = tighter squeeze required
VOLUME_SURGE_MULTIPLIER = 1.5     # Higher = more volume required

# Adjust reversal detection
RSI_OVERSOLD = 30                 # Lower = stock must be more oversold
RSI_OVERBOUGHT = 70               # Higher = stock must be more overbought

# Cache duration (seconds between API calls)
CACHE_DURATION = 30
```

---

## Project Structure

```
my-trading-helper/
├── backend/                    # Python FastAPI backend
│   ├── main.py                 # API server (endpoints)
│   ├── config.py               # All configurable settings
│   ├── data_provider.py        # Fetches data from Yahoo/Alpaca
│   ├── scanner.py              # Analyzes stocks, scores breakouts/reversals
│   ├── indicators.py           # Technical indicators (RSI, MACD, BB, etc.)
│   └── requirements.txt        # Python dependencies
├── frontend/                   # React 19 + Vite + Tailwind CSS v4
│   ├── src/
│   │   ├── App.jsx             # Root component with header/config
│   │   ├── components/
│   │   │   ├── Dashboard.jsx   # Main layout (two columns)
│   │   │   ├── StockTable.jsx  # Stock list table with color coding
│   │   │   └── ConfigPanel.jsx # Settings panel
│   │   └── hooks/
│   │       └── useStockData.js # Data fetching + auto-refresh logic
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
└── README.md
```

---

## How the Scanner Works

### Breakout Detection

A "breakout" happens when price pushes through a resistance level after consolidating. We score each stock (0–100) based on:

| Signal | Points | What It Means |
|--------|--------|---------------|
| Bollinger Band Squeeze | 0–30 | Bands are tight → price is coiling up |
| Volume Surge | 0–30 | Current volume is 1.5x+ the average |
| Near Resistance | 0–20 | Price is pressing against the upper band |
| RSI Momentum | 0–20 | RSI is building (45–65) but not overbought |

### Trend Reversal Detection

A "reversal" is when a stock changes direction. We check both bullish and bearish signals:

| Signal | Points | Bullish | Bearish |
|--------|--------|---------|---------|
| RSI Extreme | 0–25 | RSI < 30 (oversold) | RSI > 70 (overbought) |
| MACD Cross | 0–25 | MACD crosses above signal | MACD crosses below signal |
| EMA Cross | 0–25 | Fast EMA crosses above slow | Fast EMA crosses below slow |
| Momentum Shift | 0–15 | Histogram turning positive | Histogram turning negative |

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/scan?timeframe=1m&sort_by=pct_change&sort_order=desc&max_results=20` | Get scan results |
| GET | `/api/scan?force=1` | Force refresh (bypass cache) |
| GET | `/api/config` | Get current configuration |
| POST | `/api/config` | Update config (JSON body) |
| POST | `/api/refresh` | Clear cache |
| GET | `/api/health` | Health check |

---

## Important Notes

- **Market Hours**: US markets are open 9:30 AM – 4:00 PM ET, Monday–Friday. Outside these hours, you'll see the last available data.
- **Not Financial Advice**: This tool is for educational and informational purposes. Always do your own research before trading.
- **Rate Limits**: Yahoo Finance may throttle requests if you scan too aggressively. The default 30-second cache helps prevent this.
