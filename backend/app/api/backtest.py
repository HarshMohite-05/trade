from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from ..core.backtest_engine import backtest_engine, aggregate_candles, fetch_1m_range
from ..database import get_backtest_runs, get_backtest_trades
from ..utils.fno_stocks import FNO_STOCKS, get_stock_by_symbol

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])

class BacktestRequest(BaseModel):
    symbols: List[str] = ["ALL"]
    date_from: str = "2026-10-01"
    date_to: str = "2026-10-17"
    initial_capital: float = 500000.0
    risk_per_trade_pct: float = 0.5
    strategy: str = "ALL"  # 'ALL', 'ORDER_BLOCK', 'SMC_FVG'

@router.get("/stocks")
def get_backtest_stocks():
    """Returns list of all available F&O stocks for selection."""
    return [
        {"symbol": s["symbol"], "name": s["name"], "sector": s["sector"]}
        for s in FNO_STOCKS
    ]

@router.post("/run")
def run_backtest(req: BacktestRequest):
    """Executes backtesting over selected symbols and date range."""
    results = backtest_engine.run_backtest(
        symbols=req.symbols,
        date_from=req.date_from,
        date_to=req.date_to,
        initial_capital=req.initial_capital,
        risk_per_trade_pct=req.risk_per_trade_pct,
        strategy=req.strategy
    )
    return results

@router.get("/history")
def get_history(limit: int = Query(20, description="Max runs to fetch")):
    """Returns history of previous backtest executions stored in SQLite."""
    return get_backtest_runs(limit)

@router.get("/run/{run_id}/trades")
def get_run_trades(run_id: str):
    """Returns trades for a specific backtest run."""
    trades = get_backtest_trades(run_id)
    if not trades:
        raise HTTPException(status_code=404, detail="No trades found for run_id")
    return trades


_DAY_CACHE: dict = {}

@router.get("/trade-chart")
def get_trade_chart(
    symbol: str = Query(..., description="Stock symbol"),
    date: str = Query(..., description="Session date YYYY-MM-DD"),
    timeframe: str = Query("3m", description="1m, 3m or 5m")
):
    """
    Full-session candles (+ session VWAP) for one backtest trade.
    Chart times are 'IST wall-clock as UTC' epoch seconds so the axis reads in IST.
    """
    import calendar
    from datetime import datetime

    stock = get_stock_by_symbol(symbol)
    if not stock:
        raise HTTPException(status_code=404, detail="Unknown symbol")

    key = (symbol, date)
    raw = _DAY_CACHE.get(key)
    if raw is None:
        raw = [c for c in fetch_1m_range(stock.get("instrument_key", ""), date, date) if c[0][:10] == date]
        if raw:
            if len(_DAY_CACHE) > 64:
                _DAY_CACHE.clear()
            _DAY_CACHE[key] = raw
    if not raw:
        raise HTTPException(status_code=404, detail="No candles returned (check Upstox token / date)")

    step = {"1m": 1, "3m": 3, "5m": 5}.get(timeframe, 3)
    candles = aggregate_candles(raw, step)
    out = []
    for c in candles:
        out.append({
            "time": calendar.timegm(c["dt"].timetuple()),
            "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"],
            "volume": c["volume"], "vwap": c["sess_vwap"],
        })
    return {"symbol": symbol, "date": date, "timeframe": timeframe, "step_seconds": step * 60, "candles": out}
