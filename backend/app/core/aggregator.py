"""
Tick Aggregation Engine for 3-minute and 5-minute candles strictly aligned to NSE 09:15 IST open.
"""

from datetime import datetime, time
import pytz
from typing import Dict, List, Optional, Any, Callable

IST = pytz.timezone("Asia/Kolkata")
MARKET_OPEN_TIME = time(9, 15)
MARKET_CLOSE_TIME = time(15, 30)

class Candle:
    def __init__(self, symbol: str, timeframe: str, start_time: datetime, open_price: float):
        self.symbol = symbol
        self.timeframe = timeframe  # '3m' or '5m'
        self.start_time = start_time
        self.open = open_price
        self.high = open_price
        self.low = open_price
        self.close = open_price
        self.volume = 0.0
        self.tick_count = 0
        self.vwap = open_price

    def update(self, price: float, volume: float = 0.0, current_session_vwap: float = 0.0):
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += volume
        self.tick_count += 1
        if current_session_vwap > 0:
            self.vwap = current_session_vwap

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "open": round(self.open, 2),
            "high": round(self.high, 2),
            "low": round(self.low, 2),
            "close": round(self.close, 2),
            "volume": int(self.volume),
            "vwap": round(self.vwap, 2),
            "is_bullish": self.close > self.open,
            "is_bearish": self.close < self.open,
            "body": round(abs(self.close - self.open), 2),
            "range": round(self.high - self.low, 2)
        }

def get_candle_slot_start(dt: datetime, interval_minutes: int) -> datetime:
    """
    Returns the aligned start time for a candle strictly based on NSE 09:15 market open.
    interval_minutes: 3 or 5
    """
    # Convert to IST if naive or non-IST
    if dt.tzinfo is None:
        dt = IST.localize(dt)
    else:
        dt = dt.astimezone(IST)

    total_minutes_from_open = (dt.hour - 9) * 60 + (dt.minute - 15)
    if total_minutes_from_open < 0:
        # Pre-market: clamp to 09:15 slot
        slot_minutes = 0
    else:
        slot_index = total_minutes_from_open // interval_minutes
        slot_minutes = slot_index * interval_minutes

    slot_total_minutes = 9 * 60 + 15 + slot_minutes
    slot_hour = slot_total_minutes // 60
    slot_min = slot_total_minutes % 60
    return dt.replace(hour=slot_hour, minute=slot_min, second=0, microsecond=0)

class StockCandleAggregator:
    def __init__(self, symbol: str, on_candle_completed: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.symbol = symbol
        self.on_candle_completed = on_candle_completed

        # Current partial candles
        self.current_3m: Optional[Candle] = None
        self.current_5m: Optional[Candle] = None

        # Completed history (newest last)
        self.candles_3m: List[Dict[str, Any]] = []
        self.candles_5m: List[Dict[str, Any]] = []

        # Session tracking
        self.session_open_price: Optional[float] = None
        self.session_high: float = float("-inf")
        self.session_low: float = float("inf")
        self.session_cum_pv: float = 0.0
        self.session_cum_volume: float = 0.0
        self.session_vwap: float = 0.0
        self.prev_close: Optional[float] = None
        self.last_ltp: float = 0.0
        self.last_volume: float = 0.0
        self.last_timestamp: Optional[datetime] = None

    def process_tick(self, ltp: float, volume_delta: float = 0.0, dt: Optional[datetime] = None, prev_close: Optional[float] = None) -> None:
        if dt is None:
            dt = datetime.now(IST)
        elif dt.tzinfo is None:
            dt = IST.localize(dt)
        else:
            dt = dt.astimezone(IST)

        self.last_ltp = ltp
        self.last_timestamp = dt
        if prev_close:
            self.prev_close = prev_close

        # Initialize session open
        if self.session_open_price is None:
            self.session_open_price = ltp

        self.session_high = max(self.session_high, ltp)
        self.session_low = min(self.session_low, ltp)

        # Update Session VWAP
        if volume_delta > 0:
            self.session_cum_pv += ltp * volume_delta
            self.session_cum_volume += volume_delta
            self.session_vwap = self.session_cum_pv / self.session_cum_volume
        elif self.session_vwap == 0:
            self.session_vwap = ltp

        # Process 3-minute candle
        slot_3m = get_candle_slot_start(dt, 3)
        if self.current_3m is None:
            self.current_3m = Candle(self.symbol, "3m", slot_3m, ltp)
        elif self.current_3m.start_time != slot_3m:
            # Current 3m candle has finalized!
            completed_dict = self.current_3m.to_dict()
            self.candles_3m.append(completed_dict)
            if self.on_candle_completed:
                self.on_candle_completed(completed_dict)
            self.current_3m = Candle(self.symbol, "3m", slot_3m, ltp)

        self.current_3m.update(ltp, volume_delta, self.session_vwap)

        # Process 5-minute candle
        slot_5m = get_candle_slot_start(dt, 5)
        if self.current_5m is None:
            self.current_5m = Candle(self.symbol, "5m", slot_5m, ltp)
        elif self.current_5m.start_time != slot_5m:
            # Current 5m candle has finalized!
            completed_dict = self.current_5m.to_dict()
            self.candles_5m.append(completed_dict)
            if self.on_candle_completed:
                self.on_candle_completed(completed_dict)
            self.current_5m = Candle(self.symbol, "5m", slot_5m, ltp)

        self.current_5m.update(ltp, volume_delta, self.session_vwap)

    def load_historical_candles(self, timeframe: str, candles: List[Dict[str, Any]]):
        """Pre-populate completed historical candles for calculations"""
        if timeframe == "3m":
            self.candles_3m = candles.copy()
        elif timeframe == "5m":
            self.candles_5m = candles.copy()
