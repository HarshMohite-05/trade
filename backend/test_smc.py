import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.core.upstox_service import upstox_service
from app.core.backtest_engine import aggregate_candles
from app.utils.fno_stocks import get_stock_by_symbol

def test_smc_detection():
    stock = get_stock_by_symbol("HAL")
    inst_key = stock["instrument_key"]
    to_d = datetime.now().strftime("%Y-%m-%d")
    from_d = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

    raw_candles = upstox_service.get_historical_candles_range(inst_key, to_d, from_d, "1minute")
    print(f"Total 1m candles: {len(raw_candles)}")

    # Group by day
    from collections import defaultdict
    by_day = defaultdict(list)
    for c in raw_candles:
        by_day[c[0][:10]].append(c)

    for day, c1m in sorted(by_day.items()):
        c5 = aggregate_candles(c1m, 5)
        c3 = aggregate_candles(c1m, 3)
        print(f"\n--- Trading Day: {day} (5m candles: {len(c5)}, 3m candles: {len(c3)}) ---")
        
        # Test 5m FVG detection
        for i in range(2, len(c5)):
            c1 = c5[i-2]
            c2 = c5[i-1] # displacement candle
            c3_c = c5[i]

            # Bullish FVG: c3 low > c1 high
            if c3_c["low"] > c1["high"] and c2["is_bullish"] and c2["body"] >= 1.0:
                fvg_low = c1["high"]
                fvg_high = c3_c["low"]
                ce_mid = round((fvg_low + fvg_high) / 2.0, 2)
                fvg_gap = round(fvg_high - fvg_low, 2)
                print(f"  [BULLISH FVG] at {c3_c['timestamp']}: Zone ₹{fvg_low} - ₹{fvg_high} (Gap: ₹{fvg_gap}, 50% CE: ₹{ce_mid})")

            # Bearish FVG: c3 high < c1 low
            elif c3_c["high"] < c1["low"] and c2["is_bearish"] and c2["body"] >= 1.0:
                fvg_high = c1["low"]
                fvg_low = c3_c["high"]
                ce_mid = round((fvg_low + fvg_high) / 2.0, 2)
                fvg_gap = round(fvg_high - fvg_low, 2)
                print(f"  [BEARISH FVG] at {c3_c['timestamp']}: Zone ₹{fvg_low} - ₹{fvg_high} (Gap: ₹{fvg_gap}, 50% CE: ₹{ce_mid})")

if __name__ == "__main__":
    test_smc_detection()
