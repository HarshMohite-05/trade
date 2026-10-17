# Order Block First Retest Algorithmic Trading Platform (Upstox)

A full-stack, local web application that executes the **"Order Block First Retest"** strategy using the Upstox API v2, FastAPI, SQLite, and React (Vite + Tailwind CSS).

---

## 🚀 Key Features

1. **Full Universe Live Scanner**:
   - Covers the entire **NSE F&O Universe** (all cash market eligible stocks: RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, SBIN, etc.).
   - Filter by **All Stocks**, **Top 10 Bullish**, **Top 10 Bearish**, or **Active Setups**.
   - Sector filter and instant search.
   - Real-time data table with required columns:
     `Stock | Direction | Rank | Strength | LTP / VWAP | First radar time | Zone confirmed time | Zone (Low-High) | Retest time | Entry | Stop | Target (2R) | Status`
   - Real-time WebSocket live feed (`ws://localhost:8000/api/scanner/ws`).
   - Built-in **Live Simulation (Demo)** mode with real-time tick and candle streaming for testing outside market hours.

2. **Order Block First Retest Strategy Engine**:
   - **Candidate Selection**: Strength = (% change from today's open) ÷ (20-day ADR%). Refreshed every minute.
   - **Market Alignment**: Universe breadth (≥60% above/below prev close) + positive/negative sector constituent change + price vs session VWAP.
   - **5-Minute Order Block**: Breakout of preceding 6 candles high/low, real body ≥ 1.5x avg body 20, volume ≥ 1.5x avg volume 20. Zone = full low-to-high range of most recent opposite candle in prior 3 candles.
   - **3-Minute First Retest**: Zone overlap, directional close beyond boundary.
   - **Risk Management**: Entry 1 tick beyond confirmation candle, Stop = Zone boundary - (0.10 × 5m ATR14) rounded outward to tick, Target = 2R. Max 0.5% capital risk per trade.

3. **Historical Backtesting Module**:
   - Backtest on **ALL Universe Stocks** or any individual stock.
   - Custom date ranges, starting capital, and risk per trade.
   - Persistent SQLite storage (`trading.db`).
   - Summary KPIs: Total PnL, Win Rate %, Profit Factor, Max Drawdown %, Total Trades.
   - Interactive Trade Log table with Win/Loss filters, search, and trade details.

4. **Upstox Authentication & Test**:
   - Upstox API v2 OAuth authorization flow.
   - Direct Access Token entry for instant activation.
   - Standalone CLI test script (`backend/test_reliance_tick.py`) and Web UI button to pull live RELIANCE quote.

---

## 🛠️ Running Locally

The app is already configured and running locally:

- **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173)
- **FastAPI API & Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### CLI Commands:
```bash
# Test single live RELIANCE tick
.venv/bin/python backend/test_reliance_tick.py <YOUR_UPSTOX_TOKEN>

# Start Backend Server manually
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# Start Frontend manually
cd frontend && npm run dev
```
