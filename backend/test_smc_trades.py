import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.core.upstox_service import upstox_service
from app.core.backtest_engine import aggregate_candles
from app.core.strategy import round_to_tick, calculate_atr, TICK_SIZE
from app.utils.fno_stocks import get_stock_by_symbol, FNO_STOCKS

def check_smc_fvg_setup(candles_5m, min_gap_pct=0.03):
    """
    Evaluates 5m candles for SMC Liquidity Sweep + Fair Value Gap.
    Returns detected FVG zone if current completed candle is candle 3 of an FVG.
    """
    if len(candles_5m) < 22:
        return None

    c1 = candles_5m[-3]
    c2 = candles_5m[-2] # displacement candle
    c3 = candles_5m[-1]

    # Preceding 20 candles baseline
    preceding_20 = candles_5m[-22:-2]
    avg_range = sum(c["range"] for c in preceding_20) / len(preceding_20)
    avg_vol = sum(c["volume"] for c in preceding_20) / len(preceding_20)

    # Displacement candle must have range expansion and volume
    if c2["range"] < 1.2 * avg_range:
        return None

    atr = calculate_atr(candles_5m, 14)

    # Bullish FVG Check
    if c2["is_bullish"] and c3["low"] > c1["high"]:
        fvg_low = c1["high"]
        fvg_high = c3["low"]
        gap = fvg_high - fvg_low
        if gap / c2["close"] * 100.0 >= min_gap_pct:
            # Check for preceding liquidity sweep (lowest low of prior 5 candles)
            prior_5 = candles_5m[-7:-2]
            sweep_low = min(c["low"] for c in prior_5) if prior_5 else c2["low"]
            ce_mid = round((fvg_low + fvg_high) / 2.0, 2)
            return {
                "strategy": "SMC_FVG",
                "direction": "BULLISH",
                "confirmed_time": c3["timestamp"],
                "zone_high": fvg_high,
                "zone_low": fvg_low,
                "ce_mid": ce_mid,
                "sweep_level": sweep_low,
                "displacement_candle": c2,
                "atr_14": atr
            }

    # Bearish FVG Check
    elif c2["is_bearish"] and c3["high"] < c1["low"]:
        fvg_high = c1["low"]
        fvg_low = c3["high"]
        gap = fvg_high - fvg_low
        if gap / c2["close"] * 100.0 >= min_gap_pct:
            prior_5 = candles_5m[-7:-2]
            sweep_high = max(c["high"] for c in prior_5) if prior_5 else c2["high"]
            ce_mid = round((fvg_low + fvg_high) / 2.0, 2)
            return {
                "strategy": "SMC_FVG",
                "direction": "BEARISH",
                "confirmed_time": c3["timestamp"],
                "zone_high": fvg_high,
                "zone_low": fvg_low,
                "ce_mid": ce_mid,
                "sweep_level": sweep_high,
                "displacement_candle": c2,
                "atr_14": atr
            }

    return None

def test_backtest_smc():
    universe = FNO_STOCKS[:8]
    to_d = datetime.now().strftime("%Y-%m-%d")
    from_d = (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d")

    total_trades = 0
    wins = 0

    for stock in universe:
        sym = stock["symbol"]
        candles_1m = upstox_service.get_historical_candles_range(stock["instrument_key"], to_d, from_d, "1minute")
        if not candles_1m:
            continue

        from collections import defaultdict
        by_day = defaultdict(list)
        for c in candles_1m:
            by_day[c[0][:10]].append(c)

        for day, c1m in sorted(by_day.items()):
            if len(c1m) < 30:
                continue
            c5 = aggregate_candles(c1m, 5)
            c3 = aggregate_candles(c1m, 3)

            day_open = float(c1m[0][1])
            day_close = float(c1m[-1][4])
            cand_direction = "BULLISH" if day_close >= day_open else "BEARISH"

            active_smc = None

            for i in range(21, len(c5)):
                cur_5m = c5[i]
                t_str = cur_5m["timestamp"][11:16]
                if not ("09:45" <= t_str <= "14:30"):
                    continue

                if not active_smc or active_smc.get("expired"):
                    smc_res = check_smc_fvg_setup(c5[:i+1])
                    if smc_res and smc_res["direction"] == cand_direction:
                        active_smc = smc_res
                        active_smc["expired"] = False
                        active_smc["retested"] = False

                if active_smc and not active_smc.get("retested"):
                    # Check 3m retest into FVG zone
                    c3_sub = [c for c in c3 if c["dt"] <= cur_5m["dt"] and c["timestamp"] >= active_smc["confirmed_time"]]
                    for idx_3m, c_3m in enumerate(c3_sub):
                        # Overlaps FVG
                        if not (c_3m["low"] <= active_smc["zone_high"] and c_3m["high"] >= active_smc["zone_low"]):
                            continue

                        if active_smc["direction"] == "BULLISH" and c_3m["is_bullish"]:
                            entry = round(c_3m["high"] + TICK_SIZE, 2)
                            raw_stop = active_smc["sweep_level"] - (0.10 * active_smc["atr_14"])
                            sl = round(round_to_tick(raw_stop, outward=True, is_long=True), 2)
                            risk = round(entry - sl, 2)
                            if risk <= 0:
                                continue
                            tgt = round(entry + 2.0 * risk, 2)

                            # Check fill
                            subsequent_2 = c3_sub[idx_3m+1:idx_3m+3]
                            is_filled = any(fc["high"] >= entry for fc in subsequent_2)
                            if is_filled:
                                active_smc["retested"] = True
                                total_trades += 1
                                print(f"[SMC TRADE] {sym} BULLISH on {day} at {c_3m['timestamp']} Entry: ₹{entry}, SL: ₹{sl}, TGT: ₹{tgt}")
                                # Evaluate outcome on 1m
                                subs_1m = [c for c in c1m if c[0] >= c_3m['timestamp'].replace(" ", "T")]
                                for sc in subs_1m:
                                    h, l, cl = float(sc[2]), float(sc[3]), float(sc[4])
                                    if h >= tgt:
                                        wins += 1
                                        print(f"   -> TARGET HIT (+2R)")
                                        break
                                    elif l <= sl:
                                        print(f"   -> STOP LOSS HIT (-1R)")
                                        break
                                break

                        elif active_smc["direction"] == "BEARISH" and c_3m["is_bearish"]:
                            entry = round(c_3m["low"] - TICK_SIZE, 2)
                            raw_stop = active_smc["sweep_level"] + (0.10 * active_smc["atr_14"])
                            sl = round(round_to_tick(raw_stop, outward=True, is_long=False), 2)
                            risk = round(sl - entry, 2)
                            if risk <= 0:
                                continue
                            tgt = round(entry - 2.0 * risk, 2)

                            subsequent_2 = c3_sub[idx_3m+1:idx_3m+3]
                            is_filled = any(fc["low"] <= entry for fc in subsequent_2)
                            if is_filled:
                                active_smc["retested"] = True
                                total_trades += 1
                                print(f"[SMC TRADE] {sym} BEARISH on {day} at {c_3m['timestamp']} Entry: ₹{entry}, SL: ₹{sl}, TGT: ₹{tgt}")
                                subs_1m = [c for c in c1m if c[0] >= c_3m['timestamp'].replace(" ", "T")]
                                for sc in subs_1m:
                                    h, l, cl = float(sc[2]), float(sc[3]), float(sc[4])
                                    if l <= tgt:
                                        wins += 1
                                        print(f"   -> TARGET HIT (+2R)")
                                        break
                                    elif h >= sl:
                                        print(f"   -> STOP LOSS HIT (-1R)")
                                        break
                                break

    print(f"\nTotal SMC Trades: {total_trades}, Wins: {wins}, Win Rate: {round(wins/total_trades*100, 1) if total_trades else 0}%")

if __name__ == "__main__":
    test_backtest_smc()
