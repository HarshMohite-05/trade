"""
Strictly Intraday Backtesting Engine for Order Block First Retest Strategy.
Uses REAL historical 1-minute candles from the Upstox API v2.

Enforces:
- Intraday Session: 09:15 IST to 15:30 IST
- Candidate Selection: Selected stocks or Top F&O universe
- Strategy Logic: 5m Order Block breakout, 3m first retest with 1-tick entry trigger
- Entry Window: Strictly 09:45 IST to 14:30 IST.
- Compulsory Exit: Strictly squares off all open positions by 15:15 IST (EOD square-off). Zero overnight carryover.
- Risk Management: Stop = Zone boundary +/- (0.10 * 5m ATR14), Target = 2R, 0.5% capital risk per trade.
"""

import uuid
from datetime import datetime, timedelta, time
from collections import defaultdict
import pytz
from typing import List, Dict, Any, Optional

from ..utils.fno_stocks import FNO_STOCKS, get_stock_by_symbol
from .strategy import strategy_engine, OrderBlockZone, round_to_tick, TICK_SIZE
from .upstox_service import upstox_service
from ..database import save_backtest_run

IST = pytz.timezone("Asia/Kolkata")

ENTRY_WINDOW_START = time(9, 45)
ENTRY_WINDOW_END = time(14, 30)
EOD_EXIT_TIME = time(15, 15)

MAX_FETCH_DAYS = 28  # Upstox limits 1-minute history requests to ~1 month


def _make_candle(bucket: List[Any], start_dt: datetime, sess_vwap: float) -> Dict[str, Any]:
    o = float(bucket[0][1])
    h = float(max(float(x[2]) for x in bucket))
    l = float(min(float(x[3]) for x in bucket))
    cl = float(bucket[-1][4])
    v = int(sum(int(x[5]) for x in bucket))
    return {
        "timestamp": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "dt": start_dt,
        "open": o,
        "high": h,
        "low": l,
        "close": cl,
        "volume": v,
        "vwap": round((o + h + l + cl) / 4.0, 2),   # candle OHLC4 (legacy field)
        "sess_vwap": round(sess_vwap, 2),             # true session VWAP at candle close
        "is_bullish": cl > o,
        "is_bearish": cl < o,
        "body": round(abs(cl - o), 2),
        "range": round(h - l, 2)
    }


def aggregate_candles(candles_1m: List[List[Any]], interval_min: int) -> List[Dict[str, Any]]:
    """
    Aggregates raw 1-minute Upstox candles [timestamp, open, high, low, close, volume, oi]
    into custom 3-minute or 5-minute candles aligned to 09:15 IST market open.
    Each candle carries `sess_vwap`, the cumulative session VWAP (reset every day) at its close.
    """
    candles: List[Dict[str, Any]] = []
    curr_bucket: List[Any] = []
    bucket_start_dt = None
    curr_bucket_idx = -1
    curr_day = None
    cum_pv = 0.0
    cum_v = 0.0
    bucket_vwap = 0.0

    for c in candles_1m:
        # Format: '2026-10-12T09:15:00+05:30'
        dt = datetime.fromisoformat(c[0])
        mins_from_open = (dt.hour - 9) * 60 + (dt.minute - 15)
        if mins_from_open < 0:
            continue

        if dt.date() != curr_day:
            curr_day = dt.date()
            cum_pv = 0.0
            cum_v = 0.0

        vol = float(c[5])
        typical = (float(c[2]) + float(c[3]) + float(c[4])) / 3.0
        cum_pv += typical * vol
        cum_v += vol
        run_vwap = (cum_pv / cum_v) if cum_v > 0 else float(c[4])

        b_idx = mins_from_open // interval_min
        new_bucket = bucket_start_dt is None or b_idx != curr_bucket_idx or dt.date() != bucket_start_dt.date()

        if new_bucket:
            if curr_bucket:
                candles.append(_make_candle(curr_bucket, bucket_start_dt, bucket_vwap))
            curr_bucket = [c]
            curr_bucket_idx = b_idx
            bucket_start_dt = dt
        else:
            curr_bucket.append(c)
        bucket_vwap = run_vwap

    if curr_bucket and bucket_start_dt:
        candles.append(_make_candle(curr_bucket, bucket_start_dt, bucket_vwap))

    return candles


def fetch_1m_range(instrument_key: str, date_from: str, date_to: str) -> List[List[Any]]:
    """Fetches 1-minute candles in <=28 day chunks (Upstox limit), chronological."""
    d_start = datetime.strptime(date_from, "%Y-%m-%d")
    d_end = datetime.strptime(date_to, "%Y-%m-%d")
    out: List[List[Any]] = []
    cur = d_start
    while cur <= d_end:
        chunk_end = min(cur + timedelta(days=MAX_FETCH_DAYS - 1), d_end)
        out.extend(upstox_service.get_historical_candles_range(
            instrument_key=instrument_key,
            to_date=chunk_end.strftime("%Y-%m-%d"),
            from_date=cur.strftime("%Y-%m-%d"),
            interval="1minute"
        ))
        cur = chunk_end + timedelta(days=1)
    return out



class BacktestEngine:
    def __init__(self):
        pass

    def run_backtest(
        self,
        symbols: List[str],
        date_from: str,
        date_to: str,
        initial_capital: float = 500000.0,
        risk_per_trade_pct: float = 0.5,
        strategy: str = "ALL"
    ) -> Dict[str, Any]:
        """
        Runs intraday backtest using authentic Upstox API historical candles.
        strategy: 'ALL', 'ORDER_BLOCK', or 'SMC_FVG'
        """
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"
        
        is_all_universe = not symbols or "ALL" in [s.upper() for s in symbols]
        if is_all_universe:
            # For ALL universe backtest, prioritize top liquid benchmark F&O stocks
            universe = FNO_STOCKS[:12]
        else:
            sel_set = {s.upper() for s in symbols}
            universe = [s for s in FNO_STOCKS if s["symbol"] in sel_set]
            if not universe:
                universe = [get_stock_by_symbol(symbols[0])] if symbols else FNO_STOCKS[:10]

        all_trades: List[Dict[str, Any]] = []
        current_capital = initial_capital
        peak_capital = initial_capital
        max_drawdown = 0.0
        max_drawdown_pct = 0.0

        # Adjust date range formatting
        try:
            d_start = datetime.strptime(date_from, "%Y-%m-%d")
            d_end = datetime.strptime(date_to, "%Y-%m-%d")
        except Exception:
            d_end = datetime.now()
            d_start = d_end - timedelta(days=14)
            date_from = d_start.strftime("%Y-%m-%d")
            date_to = d_end.strftime("%Y-%m-%d")

        # Process each stock using REAL Upstox historical candles
        for stock in universe:
            sym = stock["symbol"]
            inst_key = stock.get("instrument_key", "")
            
            # Fetch real 1-minute candles from Upstox API v2
            raw_candles = fetch_1m_range(inst_key, date_from, date_to)

            if not raw_candles:
                # If API returned no candles for this symbol in this range, continue
                continue

            # Group 1-minute candles by trading date
            by_day = defaultdict(list)
            for c in raw_candles:
                dt_str = c[0][:10]
                by_day[dt_str].append(c)

            # Evaluate each intraday session
            for day_str in sorted(by_day.keys()):
                day_1m = by_day[day_str]
                if len(day_1m) < 25:
                    continue  # Incomplete session

                # Aggregate into 5m and 3m candles aligned to 09:15 IST
                c5 = aggregate_candles(day_1m, 5)
                c3 = aggregate_candles(day_1m, 3)

                if len(c5) < 21:
                    continue

                # Determine candidate selection bias for this trading day
                day_open = float(day_1m[0][1])
                day_close = float(day_1m[-1][4])
                pct_from_open = ((day_close - day_open) / day_open) * 100.0
                cand_direction = "BULLISH" if pct_from_open >= 0 else "BEARISH"

                active_zone: Optional[OrderBlockZone] = None

                # Step through 5m candles progressively
                for idx_5m in range(20, len(c5)):
                    cur_5m = c5[idx_5m]
                    t_str = cur_5m["timestamp"][11:16]

                    # Strategy Entry Window: 09:45 to 14:30 IST
                    if not ("09:45" <= t_str <= "14:30"):
                        continue
                    
                    # Check for 5m setup matching candidate direction based on selected strategy
                    if not active_zone or active_zone.expired:
                        # 1. Order Block Strategy Check
                        if strategy in ("ORDER_BLOCK", "ALL"):
                            ob_res = strategy_engine.check_5m_order_block(c5[:idx_5m + 1])
                            if ob_res and ob_res["direction"] == cand_direction:
                                vwap_aligned = (cur_5m["close"] >= cur_5m["vwap"]) if cand_direction == "BULLISH" else (cur_5m["close"] <= cur_5m["vwap"])
                                if vwap_aligned:
                                    active_zone = OrderBlockZone(
                                        symbol=sym,
                                        direction=ob_res["direction"],
                                        strategy_type="ORDER_BLOCK",
                                        confirmed_time=ob_res["confirmed_time"],
                                        zone_high=ob_res["zone_high"],
                                        zone_low=ob_res["zone_low"],
                                        breakout_candle=ob_res["breakout_candle"],
                                        ob_candle=ob_res["ob_candle"],
                                        atr_14=ob_res["atr_14"]
                                    )

                        # 2. SMC Liquidity + FVG Strategy Check
                        if (not active_zone) and strategy in ("SMC_FVG", "ALL"):
                            smc_res = strategy_engine.check_5m_smc_fvg(c5[:idx_5m + 1])
                            if smc_res and smc_res["direction"] == cand_direction:
                                vwap_aligned = (cur_5m["close"] >= cur_5m["vwap"]) if cand_direction == "BULLISH" else (cur_5m["close"] <= cur_5m["vwap"])
                                if vwap_aligned:
                                    active_zone = OrderBlockZone(
                                        symbol=sym,
                                        direction=smc_res["direction"],
                                        strategy_type="SMC_FVG",
                                        confirmed_time=smc_res["confirmed_time"],
                                        zone_high=smc_res["zone_high"],
                                        zone_low=smc_res["zone_low"],
                                        breakout_candle=smc_res["breakout_candle"],
                                        ob_candle=smc_res.get("ob_candle"),
                                        atr_14=smc_res["atr_14"],
                                        ce_mid=smc_res.get("ce_mid"),
                                        sweep_level=smc_res.get("sweep_level")
                                    )

                    # Check for 3m first retest if zone active and not yet retested
                    if active_zone and not active_zone.retested and not active_zone.expired:
                        c3_sub = [c for c in c3 if c["dt"] <= cur_5m["dt"]]
                        session_high = max(c["high"] for c in c5[:idx_5m + 1])
                        session_low = min(c["low"] for c in c5[:idx_5m + 1])

                        retest_res = strategy_engine.check_3m_retest(
                            zone=active_zone,
                            completed_3m_candles=c3_sub,
                            session_high=session_high,
                            session_low=session_low,
                            session_vwap=cur_5m["vwap"]
                        )

                        # Only enter trade if order was actually FILLED within the next 2 candles
                        if retest_res and retest_res.get("is_filled"):
                            active_zone.retested = True
                            entry_dt_str = retest_res["fill_time"]
                            entry_p = retest_res["entry_price"]
                            sl_p = retest_res["stop_loss"]
                            tgt_p = retest_res["target"]
                            direction = retest_res["direction"]

                            # Risk Management & Position Sizing (0.5% capital risk)
                            risk_amt = current_capital * (risk_per_trade_pct / 100.0)
                            sl_dist = abs(entry_p - sl_p)
                            shares = max(1, int(risk_amt / sl_dist)) if sl_dist > 0 else 1

                            # Simulate Trade Execution on subsequent 1-minute Upstox candles
                            entry_iso = entry_dt_str.replace(" ", "T")
                            subsequent_candles = [c for c in day_1m if c[0] >= entry_iso]

                            exit_p = None
                            exit_time = None
                            exit_reason = None

                            for sc in subsequent_candles:
                                ts, o, h, l, cl, vol, oi = sc
                                t_str = ts[11:16]  # 'HH:MM'

                                if direction == "BULLISH":
                                    if float(h) >= tgt_p:
                                        exit_p = tgt_p
                                        exit_time = ts.replace("T", " ")[:19]
                                        exit_reason = "TARGET_HIT (2R)"
                                        break
                                    elif float(l) <= sl_p:
                                        exit_p = sl_p
                                        exit_time = ts.replace("T", " ")[:19]
                                        exit_reason = "STOP_LOSS_HIT"
                                        break
                                else:  # BEARISH
                                    if float(l) <= tgt_p:
                                        exit_p = tgt_p
                                        exit_time = ts.replace("T", " ")[:19]
                                        exit_reason = "TARGET_HIT (2R)"
                                        break
                                    elif float(h) >= sl_p:
                                        exit_p = sl_p
                                        exit_time = ts.replace("T", " ")[:19]
                                        exit_reason = "STOP_LOSS_HIT"
                                        break

                                # Compulsory Intraday 15:15 IST Square-Off
                                if t_str >= "15:15":
                                    exit_p = float(cl)
                                    exit_time = ts.replace("T", " ")[:19]
                                    exit_reason = "EOD_1515_SQUAREOFF"
                                    break

                            # Fallback if market closed before 15:15
                            if not exit_p and subsequent_candles:
                                exit_p = float(subsequent_candles[-1][4])
                                exit_time = subsequent_candles[-1][0].replace("T", " ")[:19]
                                exit_reason = "EOD_1515_SQUAREOFF"

                            if exit_p:
                                if direction == "BULLISH":
                                    pnl = (exit_p - entry_p) * shares
                                else:
                                    pnl = (entry_p - exit_p) * shares

                                pnl = round(pnl, 2)
                                current_capital += pnl
                                pnl_pct = round((pnl / (entry_p * shares)) * 100.0, 2)
                                r_mult = round(pnl / risk_amt, 2) if risk_amt > 0 else 0.0

                                # Track Drawdown
                                peak_capital = max(peak_capital, current_capital)
                                dd = peak_capital - current_capital
                                dd_pct = (dd / peak_capital * 100.0) if peak_capital > 0 else 0.0
                                if dd > max_drawdown:
                                    max_drawdown = dd
                                    max_drawdown_pct = dd_pct

                                all_trades.append({
                                    "symbol": sym,
                                    "name": stock["name"],
                                    "direction": direction,
                                    "strategy": active_zone.strategy_type,
                                    "session_date": day_str,
                                    "confirmation_time": active_zone.confirmed_time,
                                    "zone_high": active_zone.zone_high,
                                    "zone_low": active_zone.zone_low,
                                    "ce_mid": getattr(active_zone, "ce_mid", None),
                                    "retest_time": entry_dt_str,
                                    "entry_time": entry_dt_str,
                                    "entry_price": entry_p,
                                    "stop_loss": sl_p,
                                    "target": tgt_p,
                                    "shares": shares,
                                    "exit_time": exit_time,
                                    "exit_price": round(exit_p, 2),
                                    "pnl": pnl,
                                    "pnl_pct": pnl_pct,
                                    "r_multiple": r_mult,
                                    "status": "WIN" if pnl > 0 else "LOSS",
                                    "exit_reason": exit_reason,
                                    "capital_after_trade": round(current_capital, 2)
                                })
                                break

        # Sort all trades chronologically
        all_trades.sort(key=lambda t: t.get("entry_time", ""))

        total_trades = len(all_trades)
        wins = len([t for t in all_trades if t["pnl"] > 0])
        losses = len([t for t in all_trades if t["pnl"] < 0])
        eod_exits = len([t for t in all_trades if "EOD_1515" in t.get("exit_reason", "")])
        win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_profit = sum(t["pnl"] for t in all_trades if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in all_trades if t["pnl"] < 0))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        total_pnl = current_capital - initial_capital
        total_pnl_pct = (total_pnl / initial_capital * 100.0)

        symbols_display = "ALL (" + str(len(universe)) + " stocks)" if is_all_universe else ", ".join(s["symbol"] for s in universe)

        strategy_labels = {
            "ALL": "Multi-Strategy (Order Block & SMC Liquidity FVG)",
            "ORDER_BLOCK": "Order Block First Retest",
            "SMC_FVG": "SMC Liquidity Sweep + Fair Value Gap (FVG)"
        }

        summary = {
            "id": run_id,
            "created_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
            "strategy": strategy_labels.get(strategy, strategy),
            "symbols": symbols_display,
            "date_from": date_from,
            "date_to": date_to,
            "intraday_entry_window": "09:45 - 14:30 IST",
            "compulsory_square_off": "15:15 IST",
            "initial_capital": round(initial_capital, 2),
            "final_capital": round(current_capital, 2),
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "eod_square_offs": eod_exits,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "profit_factor": profit_factor,
            "max_drawdown": round(max_drawdown, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "avg_trade_pnl": round(total_pnl / total_trades, 2) if total_trades > 0 else 0.0
        }

        # Save to SQLite database
        try:
            save_backtest_run(summary, all_trades)
        except Exception as e:
            print(f"Error saving to db: {e}")

        return {
            "summary": summary,
            "trades": all_trades
        }

backtest_engine = BacktestEngine()
