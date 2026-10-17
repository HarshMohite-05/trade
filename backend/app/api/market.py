from fastapi import APIRouter, HTTPException, Query
from ..core.upstox_service import upstox_service
from ..config import current_settings

router = APIRouter(prefix="/api/market", tags=["Market"])

RELIANCE_INSTRUMENT_KEY = "NSE_EQ|INE002A01018"

@router.get("/tick")
def get_single_tick(instrument_key: str = Query(RELIANCE_INSTRUMENT_KEY, description="Upstox instrument key")):
    """
    Pulls a live tick / quote of a given instrument (defaults to RELIANCE).
    """
    if not current_settings.access_token:
        raise HTTPException(
            status_code=401,
            detail="Upstox Access Token is not set. Please authenticate first via /api/auth/."
        )
    
    quote_res = upstox_service.get_market_quote(instrument_key)
    if quote_res.get("status") == "error":
        raise HTTPException(status_code=500, detail=quote_res.get("message"))
    
    return quote_res

@router.get("/ltp")
def get_ltp(instrument_key: str = Query(RELIANCE_INSTRUMENT_KEY)):
    if not current_settings.access_token:
        raise HTTPException(status_code=401, detail="Upstox Access Token is not set.")
    return upstox_service.get_ltp(instrument_key)

@router.get("/candles")
def get_stock_candles(
    symbol: str = Query("HAL", description="Stock Symbol"),
    timeframe: str = Query("5m", description="Timeframe: 5m, 3m, or 1m")
):
    """
    Returns authentic Upstox candlestick data and active strategy levels (Zone, Entry, Stop, Target)
    for interactive charting.
    """
    from datetime import datetime, timedelta
    from ..utils.fno_stocks import get_stock_by_symbol
    from ..core.backtest_engine import aggregate_candles
    from ..core.scanner_engine import scanner_manager

    stock = get_stock_by_symbol(symbol)
    inst_key = stock.get("instrument_key", "")

    to_d = datetime.now().strftime("%Y-%m-%d")
    from_d = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")

    raw = upstox_service.get_historical_candles_range(inst_key, to_d, from_d, "1minute")
    if not raw:
        return {"symbol": symbol, "timeframe": timeframe, "candles": [], "levels": None}

    interval_mins = 5 if timeframe == "5m" else (3 if timeframe == "3m" else 1)
    aggregated = aggregate_candles(raw, interval_mins) if interval_mins > 1 else [
        {
            "dt": datetime.fromisoformat(c[0]),
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4]),
            "volume": int(c[5])
        } for c in raw
    ]

    chart_candles = []
    for c in aggregated[-120:]:
        chart_candles.append({
            "time": int(c["dt"].timestamp()),
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c["volume"]
        })

    # Strategy levels from scanner manager if available
    levels = None
    if symbol in scanner_manager.items:
        it = scanner_manager.items[symbol]
        levels = {
            "strategy_type": it.strategy_type,
            "zone_high": it.zone_high,
            "zone_low": it.zone_low,
            "ce_mid": it.ce_mid,
            "entry_price": it.entry,
            "stop_loss": it.stop,
            "target": it.target,
            "direction": it.direction,
            "status": it.status,
            "retest_time": it.retest_time,
            "confirmed_time": it.zone_confirmed_time
        }

    return {
        "symbol": symbol,
        "name": stock.get("name", symbol),
        "timeframe": timeframe,
        "candles": chart_candles,
        "levels": levels
    }
