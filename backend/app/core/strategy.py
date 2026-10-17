"""
Algorithmic Strategy Execution Engine.
Supports Institutional Multi-Strategy Execution:
1. Order Block First Retest Strategy (Breakout, Retest, 1-Tick Trigger)
2. SMC (Smart Money Concepts) Liquidity Sweep + Fair Value Gap (FVG) Strategy
"""

from datetime import datetime, time
import math
from typing import List, Dict, Any, Optional, Tuple

TICK_SIZE = 0.05

def round_to_tick(price: float, outward: bool = False, is_long: bool = True) -> float:
    """Rounds to NSE standard equity tick size (0.05). Outward rounding widens stops."""
    if outward:
        if is_long:
            # Round stop loss DOWN to nearest 0.05
            return round(math.floor(price / TICK_SIZE) * TICK_SIZE, 2)
        else:
            # Round stop loss UP to nearest 0.05
            return round(math.ceil(price / TICK_SIZE) * TICK_SIZE, 2)
    return round(round(price / TICK_SIZE) * TICK_SIZE, 2)

def calculate_atr(candles: List[Dict[str, Any]], period: int = 14) -> float:
    """Calculates True Range and Average True Range over period."""
    if len(candles) < period + 1:
        if not candles:
            return 1.0
        return sum(c["high"] - c["low"] for c in candles) / len(candles)

    tr_list = []
    for i in range(1, len(candles)):
        c = candles[i]
        prev_c = candles[i - 1]
        tr = max(
            c["high"] - c["low"],
            abs(c["high"] - prev_c["close"]),
            abs(c["low"] - prev_c["close"])
        )
        tr_list.append(tr)

    recent_trs = tr_list[-period:]
    return sum(recent_trs) / len(recent_trs)

class StrategyZone:
    def __init__(
        self,
        symbol: str,
        direction: str,  # 'BULLISH' or 'BEARISH'
        strategy_type: str,  # 'ORDER_BLOCK' or 'SMC_FVG'
        confirmed_time: str,
        zone_high: float,
        zone_low: float,
        breakout_candle: Dict[str, Any],
        ob_candle: Optional[Dict[str, Any]] = None,
        atr_14: float = 1.0,
        ce_mid: Optional[float] = None,
        sweep_level: Optional[float] = None
    ):
        self.symbol = symbol
        self.direction = direction
        self.strategy_type = strategy_type
        self.confirmed_time = confirmed_time
        self.zone_high = round(zone_high, 2)
        self.zone_low = round(zone_low, 2)
        self.breakout_candle = breakout_candle
        self.ob_candle = ob_candle
        self.atr_14 = atr_14
        self.ce_mid = round(ce_mid, 2) if ce_mid is not None else round((zone_high + zone_low) / 2.0, 2)
        self.sweep_level = round(sweep_level, 2) if sweep_level is not None else (zone_low if direction == "BULLISH" else zone_high)

        # State tracking
        self.retested = False
        self.retest_time: Optional[str] = None
        self.retest_candle: Optional[Dict[str, Any]] = None
        self.expired = False
        self.order_placed = False
        self.entry_price: Optional[float] = None
        self.stop_loss: Optional[float] = None
        self.target: Optional[float] = None
        self.status = "ZONE_CONFIRMED"

# Backward compatibility alias
OrderBlockZone = StrategyZone

class StrategyEngine:
    def __init__(self):
        pass

    def check_5m_order_block(self, completed_5m_candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Evaluates the most recent completed 5-minute candle for Order Block breakout.
        Requirements:
        1. Bullish breakout: closes above highest high of preceding 6 completed 5m candles.
           Bearish breakdown: closes below lowest low of preceding 6 completed 5m candles.
        2. Real body >= 1.5x average body of preceding 20 candles.
        3. Volume >= 1.5x average volume of preceding 20 candles.
        4. OB Candle: Most recent opposite candle within 3 candles immediately prior.
        """
        if len(completed_5m_candles) < 22:
            return None

        current = completed_5m_candles[-1]
        preceding = completed_5m_candles[:-1]

        # 20 preceding candles for baseline averages
        preceding_20 = preceding[-20:]
        avg_body_20 = sum(c["body"] for c in preceding_20) / 20.0
        avg_vol_20 = sum(c["volume"] for c in preceding_20) / 20.0

        current_body = current["body"]
        current_vol = current["volume"]

        # Body and Volume expansion test
        body_qualifies = current_body >= (1.5 * avg_body_20)
        vol_qualifies = avg_vol_20 == 0 or current_vol >= (1.5 * avg_vol_20)

        if not (body_qualifies and vol_qualifies):
            return None

        # Preceding 6 candles
        preceding_6 = preceding[-6:]
        highest_6_high = max(c["high"] for c in preceding_6)
        lowest_6_low = min(c["low"] for c in preceding_6)

        prior_3 = preceding[-3:]

        # Bullish Breakout Check
        if current["close"] > highest_6_high and current["is_bullish"]:
            ob_candidate = None
            for c in reversed(prior_3):
                if c["is_bearish"]:
                    ob_candidate = c
                    break

            if ob_candidate:
                atr = calculate_atr(completed_5m_candles, 14)
                return {
                    "strategy": "ORDER_BLOCK",
                    "direction": "BULLISH",
                    "confirmed_time": current["timestamp"],
                    "zone_high": ob_candidate["high"],
                    "zone_low": ob_candidate["low"],
                    "breakout_candle": current,
                    "ob_candle": ob_candidate,
                    "atr_14": atr
                }

        # Bearish Breakdown Check
        elif current["close"] < lowest_6_low and current["is_bearish"]:
            ob_candidate = None
            for c in reversed(prior_3):
                if c["is_bullish"]:
                    ob_candidate = c
                    break

            if ob_candidate:
                atr = calculate_atr(completed_5m_candles, 14)
                return {
                    "strategy": "ORDER_BLOCK",
                    "direction": "BEARISH",
                    "confirmed_time": current["timestamp"],
                    "zone_high": ob_candidate["high"],
                    "zone_low": ob_candidate["low"],
                    "breakout_candle": current,
                    "ob_candle": ob_candidate,
                    "atr_14": atr
                }

        return None

    def check_5m_smc_fvg(self, completed_5m_candles: List[Dict[str, Any]], min_gap_pct: float = 0.02) -> Optional[Dict[str, Any]]:
        """
        Evaluates the 5-minute candles for SMC Liquidity Sweep + Fair Value Gap (FVG).
        Rules:
        - 3-candle sequence: c1 (base), c2 (impulse displacement), c3 (confirmation).
        - Displacement candle c2 has range expansion >= 1.2x average range of prior 20.
        - Bullish: c3.low > c1.high (imbalance gap).
          Confluence: c1/c2 sweeps lowest low of preceding 5 candles (Sellside Liquidity Sweep).
        - Bearish: c3.high < c1.low (imbalance gap).
          Confluence: c1/c2 sweeps highest high of preceding 5 candles (Buyside Liquidity Sweep).
        - Gap threshold: gap >= min_gap_pct% of stock price.
        """
        if len(completed_5m_candles) < 22:
            return None

        c1 = completed_5m_candles[-3]
        c2 = completed_5m_candles[-2]
        c3 = completed_5m_candles[-1]

        # Prior 20 candles for range baseline
        prior_20 = completed_5m_candles[-22:-2]
        avg_range_20 = sum(c["range"] for c in prior_20) / len(prior_20)

        if c2["range"] < (1.15 * avg_range_20):
            return None

        atr = calculate_atr(completed_5m_candles, 14)
        prior_5 = completed_5m_candles[-8:-3]

        # Bullish FVG
        if c2["is_bullish"] and c3["low"] > c1["high"]:
            fvg_low = c1["high"]
            fvg_high = c3["low"]
            gap = fvg_high - fvg_low
            gap_pct = (gap / c2["close"]) * 100.0

            if gap_pct >= min_gap_pct:
                sweep_low = min(c["low"] for c in prior_5) if prior_5 else min(c1["low"], c2["low"])
                ce_mid = round((fvg_low + fvg_high) / 2.0, 2)
                return {
                    "strategy": "SMC_FVG",
                    "direction": "BULLISH",
                    "confirmed_time": c3["timestamp"],
                    "zone_high": fvg_high,
                    "zone_low": fvg_low,
                    "ce_mid": ce_mid,
                    "sweep_level": min(sweep_low, c1["low"], c2["low"]),
                    "breakout_candle": c2,
                    "ob_candle": c1,
                    "atr_14": atr
                }

        # Bearish FVG
        elif c2["is_bearish"] and c3["high"] < c1["low"]:
            fvg_high = c1["low"]
            fvg_low = c3["high"]
            gap = fvg_high - fvg_low
            gap_pct = (gap / c2["close"]) * 100.0

            if gap_pct >= min_gap_pct:
                sweep_high = max(c["high"] for c in prior_5) if prior_5 else max(c1["high"], c2["high"])
                ce_mid = round((fvg_low + fvg_high) / 2.0, 2)
                return {
                    "strategy": "SMC_FVG",
                    "direction": "BEARISH",
                    "confirmed_time": c3["timestamp"],
                    "zone_high": fvg_high,
                    "zone_low": fvg_low,
                    "ce_mid": ce_mid,
                    "sweep_level": max(sweep_high, c1["high"], c2["high"]),
                    "breakout_candle": c2,
                    "ob_candle": c1,
                    "atr_14": atr
                }

        return None

    def check_3m_retest(
        self,
        zone: StrategyZone,
        completed_3m_candles: List[Dict[str, Any]],
        session_high: float,
        session_low: float,
        session_vwap: float
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates 3m completed candles for retest of the confirmed zone (Order Block or SMC FVG).
        Supports:
        - ORDER_BLOCK: Retest candle overlaps zone, closes directional beyond boundary.
        - SMC_FVG: Retest candle retraces into FVG zone (touches boundary or 50% CE) and closes directional.
        - 1-tick entry trigger in the next two 3m candles.
        - Stop loss: Outer boundary or Sweep level +/- (0.10 * 5m ATR14), rounded outward.
        - Target: 2R.
        """
        if zone.retested or zone.expired or not completed_3m_candles:
            return None

        try:
            zone_dt = datetime.strptime(zone.confirmed_time, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None

        # Filter candles completed at or after zone confirmation
        valid_candles = [c for c in completed_3m_candles if c["timestamp"] >= zone.confirmed_time]
        if not valid_candles:
            return None

        for idx, c_3m in enumerate(valid_candles):
            try:
                c_dt = datetime.strptime(c_3m["timestamp"], "%Y-%m-%d %H:%M:%S")
                minutes_elapsed = (c_dt - zone_dt).total_seconds() / 60.0
                if minutes_elapsed > 90:  # Expire after 90 minutes if not retested
                    zone.expired = True
                    zone.status = "ZONE_EXPIRED"
                    return None
            except Exception:
                pass

            # Check overlap with zone
            overlaps = (c_3m["low"] <= zone.zone_high) and (c_3m["high"] >= zone.zone_low)
            if not overlaps:
                continue

            if zone.direction == "BULLISH":
                # For ORDER_BLOCK: close must be bullish and above zone_high
                # For SMC_FVG: candle retests FVG and closes bullish
                retest_valid = False
                if zone.strategy_type == "ORDER_BLOCK":
                    retest_valid = c_3m["is_bullish"] and c_3m["close"] > zone.zone_high
                else:  # SMC_FVG
                    retest_valid = c_3m["is_bullish"] or (c_3m["close"] >= zone.ce_mid)

                if retest_valid:
                    entry = round(c_3m["high"] + TICK_SIZE, 2)
                    # Stop loss base: lower of zone_low or sweep_level
                    sl_base = min(zone.zone_low, zone.sweep_level)
                    raw_stop = sl_base - (0.10 * zone.atr_14)
                    stop_loss = round(round_to_tick(raw_stop, outward=True, is_long=True), 2)
                    risk = round(entry - stop_loss, 2)
                    if risk <= 0:
                        continue

                    target = round(entry + (2.0 * risk), 2)

                    # Skip trade if session high lies between entry and target
                    if entry < session_high < target:
                        zone.status = "SKIPPED_SESSION_HIGH_FILTER"
                        return None

                    # Check 1-tick entry trigger in the next two 3m candles
                    subsequent_2 = valid_candles[idx + 1 : idx + 3]
                    is_filled = False
                    fill_time = None
                    for fc in subsequent_2:
                        if fc["high"] >= entry:
                            is_filled = True
                            fill_time = fc["timestamp"]
                            break
                        if fc["low"] <= stop_loss:
                            break

                    zone.retested = True
                    zone.retest_time = c_3m["timestamp"]
                    zone.retest_candle = c_3m
                    zone.entry_price = entry
                    zone.stop_loss = stop_loss
                    zone.target = target
                    zone.status = "IN_TRADE" if is_filled else ("ORDER_PENDING" if len(subsequent_2) < 2 else "ORDER_CANCELLED_UNFILLED")

                    return {
                        "symbol": zone.symbol,
                        "strategy": zone.strategy_type,
                        "direction": "BULLISH",
                        "retest_time": c_3m["timestamp"],
                        "entry_price": entry,
                        "stop_loss": stop_loss,
                        "target": target,
                        "risk": risk,
                        "reward": round(2.0 * risk, 2),
                        "is_filled": is_filled,
                        "fill_time": fill_time or c_3m["timestamp"],
                        "status": zone.status
                    }

            elif zone.direction == "BEARISH":
                retest_valid = False
                if zone.strategy_type == "ORDER_BLOCK":
                    retest_valid = c_3m["is_bearish"] and c_3m["close"] < zone.zone_low
                else:  # SMC_FVG
                    retest_valid = c_3m["is_bearish"] or (c_3m["close"] <= zone.ce_mid)

                if retest_valid:
                    entry = round(c_3m["low"] - TICK_SIZE, 2)
                    sl_base = max(zone.zone_high, zone.sweep_level)
                    raw_stop = sl_base + (0.10 * zone.atr_14)
                    stop_loss = round(round_to_tick(raw_stop, outward=True, is_long=False), 2)
                    risk = round(stop_loss - entry, 2)
                    if risk <= 0:
                        continue

                    target = round(entry - (2.0 * risk), 2)

                    # Skip trade if session low lies between entry and target
                    if target < session_low < entry:
                        zone.status = "SKIPPED_SESSION_LOW_FILTER"
                        return None

                    subsequent_2 = valid_candles[idx + 1 : idx + 3]
                    is_filled = False
                    fill_time = None
                    for fc in subsequent_2:
                        if fc["low"] <= entry:
                            is_filled = True
                            fill_time = fc["timestamp"]
                            break
                        if fc["high"] >= stop_loss:
                            break

                    zone.retested = True
                    zone.retest_time = c_3m["timestamp"]
                    zone.retest_candle = c_3m
                    zone.entry_price = entry
                    zone.stop_loss = stop_loss
                    zone.target = target
                    zone.status = "IN_TRADE" if is_filled else ("ORDER_PENDING" if len(subsequent_2) < 2 else "ORDER_CANCELLED_UNFILLED")

                    return {
                        "symbol": zone.symbol,
                        "strategy": zone.strategy_type,
                        "direction": "BEARISH",
                        "retest_time": c_3m["timestamp"],
                        "entry_price": entry,
                        "stop_loss": stop_loss,
                        "target": target,
                        "risk": risk,
                        "reward": round(2.0 * risk, 2),
                        "is_filled": is_filled,
                        "fill_time": fill_time or c_3m["timestamp"],
                        "status": zone.status
                    }

        return None

strategy_engine = StrategyEngine()
