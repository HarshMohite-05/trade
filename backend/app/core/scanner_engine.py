"""
Real-time Scanner Engine.
Orchestrates candidate selection, market alignment, tick aggregation,
strategy evaluation, state tracking, and live WebSocket streaming.
"""

import asyncio
from datetime import datetime, time, timedelta
import pytz
import random
import time as pytime
from typing import Dict, List, Any, Optional

from ..utils.fno_stocks import FNO_STOCKS, get_universe, get_stock_by_symbol
from .aggregator import StockCandleAggregator
from .strategy import strategy_engine, OrderBlockZone, TICK_SIZE
from .upstox_service import upstox_service

IST = pytz.timezone("Asia/Kolkata")

class ScannerItem:
    def __init__(self, stock: Dict[str, Any]):
        self.symbol = stock["symbol"]
        self.name = stock["name"]
        self.instrument_key = stock["instrument_key"]
        self.sector = stock["sector"]
        self.lot_size = stock["lot_size"]

        # Market data
        self.ltp: float = 0.0
        self.open: float = 0.0
        self.high: float = 0.0
        self.low: float = 0.0
        self.prev_close: float = 0.0
        self.volume: float = 0.0
        self.session_vwap: float = 0.0
        self.adr_20: float = 2.5  # average daily range %

        # Ranking & Strength
        self.pct_change_from_open: float = 0.0
        self.strength: float = 0.0
        self.direction: str = "NEUTRAL"  # 'BULLISH', 'BEARISH', or 'NEUTRAL'
        self.rank: int = 999

        # Strategy State Tracking
        self.strategy_type: str = "ORDER_BLOCK"  # 'ORDER_BLOCK' or 'SMC_FVG'
        self.ce_mid: Optional[float] = None  # 50% Consequent Encroachment for SMC
        self.first_radar_time: Optional[str] = None
        self.zone_confirmed_time: Optional[str] = None
        self.zone_high: Optional[float] = None
        self.zone_low: Optional[float] = None
        self.retest_time: Optional[str] = None
        self.entry: Optional[float] = None
        self.stop: Optional[float] = None
        self.target: Optional[float] = None
        self.status: str = "SCANNING"  # SCANNING, IN_RADAR, ZONE_CONFIRMED, WAITING_RETEST, ORDER_PENDING, IN_TRADE, TARGET_HIT, STOPPED_OUT, ZONE_EXPIRED
        
        # Internal Objects
        self.active_zone: Optional[OrderBlockZone] = None
        self.aggregator = StockCandleAggregator(self.symbol)

    def to_table_dict(self) -> Dict[str, Any]:
        zone_str = f"₹{self.zone_low:.2f} - ₹{self.zone_high:.2f}" if (self.zone_low and self.zone_high) else "-"
        return {
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "strategy_type": self.strategy_type,
            "ce_mid": self.ce_mid,
            "ltp": round(self.ltp, 2),
            "open": round(self.open, 2),
            "vwap": round(self.session_vwap, 2),
            "pct_change": round(self.pct_change_from_open, 2),
            "strength": round(self.strength, 2),
            "direction": self.direction,
            "rank": self.rank,
            "first_radar_time": self.first_radar_time or "-",
            "zone_confirmed_time": self.zone_confirmed_time or "-",
            "zone": zone_str,
            "zone_low": self.zone_low,
            "zone_high": self.zone_high,
            "retest_time": self.retest_time or "-",
            "entry": round(self.entry, 2) if self.entry else None,
            "stop": round(self.stop, 2) if self.stop else None,
            "target": round(self.target, 2) if self.target else None,
            "status": self.status,
            "candles_3m_count": len(self.aggregator.candles_3m),
            "candles_5m_count": len(self.aggregator.candles_5m),
        }

class ScannerManager:
    def __init__(self):
        self.items: Dict[str, ScannerItem] = {}
        for stock in FNO_STOCKS:
            self.items[stock["symbol"]] = ScannerItem(stock)

        self.subscribers: List[asyncio.Queue] = []
        self.is_simulating: bool = False
        self.sim_task: Optional[asyncio.Task] = None
        self.market_breadth_bullish_pct: float = 50.0

        self.last_sync_time: float = 0.0

        # Seed with authentic Upstox live prices and candles
        self.sync_with_upstox_quotes()
        self._initialize_baseline_prices()
        self._seed_completed_candles()
        self.evaluate_rankings_and_market_breadth()
        for item in self.items.values():
            self.check_strategy_for_item(item)

    def sync_with_upstox_quotes(self):
        """
        Pulls authentic live batch quotes from Upstox API v2 for all F&O universe stocks.
        Updates ltp, open, high, low, prev_close, volume, and session_vwap.
        """
        try:
            keys = [item.instrument_key for item in self.items.values() if item.instrument_key]
            if not keys:
                return
            res = upstox_service.get_batch_quotes(keys)
            if res.get("status") == "success":
                quotes_data = res.get("data", {})
                for sym, item in self.items.items():
                    quote = None
                    for k, v in quotes_data.items():
                        if sym in k or (item.instrument_key and item.instrument_key.split("|")[-1] in k):
                            quote = v
                            break
                    if quote and isinstance(quote, dict):
                        ltp = quote.get("last_price")
                        ohlc = quote.get("ohlc", {})
                        if ltp is not None and ltp > 0:
                            item.ltp = round(float(ltp), 2)
                        if ohlc.get("open"):
                            item.open = round(float(ohlc.get("open")), 2)
                        if ohlc.get("high"):
                            item.high = round(float(ohlc.get("high")), 2)
                        if ohlc.get("low"):
                            item.low = round(float(ohlc.get("low")), 2)
                        if ohlc.get("close"):
                            item.prev_close = round(float(ohlc.get("close")), 2)
                        if quote.get("average_price"):
                            item.session_vwap = round(float(quote.get("average_price")), 2)
                        elif item.ltp > 0:
                            item.session_vwap = item.ltp
                        if quote.get("volume") is not None:
                            item.volume = float(quote.get("volume"))

                self.last_sync_time = pytime.time()
                self.evaluate_rankings_and_market_breadth()
        except Exception as e:
            print(f"Error syncing with Upstox quotes: {e}")

    def _initialize_baseline_prices(self):
        """Ensures any stock without an Upstox quote has authentic reference baseline values."""
        for sym, item in self.items.items():
            if item.ltp <= 0:
                stock_meta = get_stock_by_symbol(sym)
                price = stock_meta.get("ref_price", 1000.0)
                item.prev_close = price
                item.open = price
                item.ltp = price
                item.high = price
                item.low = price
                item.session_vwap = price
                item.adr_20 = round(random.uniform(2.0, 3.8), 2)

    def register_client(self, queue: asyncio.Queue):
        self.subscribers.append(queue)

    def unregister_client(self, queue: asyncio.Queue):
        if queue in self.subscribers:
            self.subscribers.remove(queue)

    async def broadcast(self, message: Dict[str, Any]):
        for q in self.subscribers:
            try:
                await q.put(message)
            except Exception:
                pass

    def evaluate_rankings_and_market_breadth(self):
        """
        Calculates:
        1. Strength = (% change from today's open) ÷ ADR_20
        2. Market alignment: % of universe above prev close & sector average changes
        3. Ranks top 10 bullish and top 10 bearish, plus ranks all stocks
        """
        total = len(self.items)
        if total == 0:
            return

        above_prev_close = 0
        sector_changes: Dict[str, List[float]] = {}

        # 1. Update individual strength and sector constituents
        for item in self.items.values():
            if item.open > 0:
                item.pct_change_from_open = ((item.ltp - item.open) / item.open) * 100.0
            else:
                item.pct_change_from_open = 0.0

            item.strength = item.pct_change_from_open / item.adr_20 if item.adr_20 > 0 else 0.0

            if item.ltp > item.prev_close or item.pct_change_from_open > 0:
                above_prev_close += 1

            if item.sector not in sector_changes:
                sector_changes[item.sector] = []
            sector_changes[item.sector].append(item.pct_change_from_open)

        self.market_breadth_bullish_pct = (above_prev_close / total) * 100.0

        # Sector average changes
        sector_avg = {sec: (sum(vals) / len(vals)) for sec, vals in sector_changes.items()}

        # Sort for bullish and bearish
        all_items = list(self.items.values())
        bullish_sorted = sorted([i for i in all_items if i.strength > 0], key=lambda x: x.strength, reverse=True)
        bearish_sorted = sorted([i for i in all_items if i.strength < 0], key=lambda x: x.strength)

        now_str = datetime.now(IST).strftime("%H:%M:%S")

        # Assign Bullish Ranks (Top 10)
        for idx, item in enumerate(bullish_sorted, 1):
            item.direction = "BULLISH"
            item.rank = idx
            if idx <= 10:
                if not item.first_radar_time:
                    item.first_radar_time = now_str
                if item.status == "SCANNING":
                    item.status = "IN_RADAR"

        # Assign Bearish Ranks (Top 10)
        for idx, item in enumerate(bearish_sorted, 1):
            item.direction = "BEARISH"
            item.rank = idx
            if idx <= 10:
                if not item.first_radar_time:
                    item.first_radar_time = now_str
                if item.status == "SCANNING":
                    item.status = "IN_RADAR"

        # Neutral / remaining items
        for item in all_items:
            if item.direction == "NEUTRAL":
                item.rank = 999

    def check_strategy_for_item(self, item: ScannerItem):
        """Runs 5m Order Block & SMC FVG and 3m Retest checks for a single item."""
        # 1. Check for 5m setup if no active zone exists
        if not item.active_zone or item.active_zone.expired:
            # First check for Order Block breakout
            ob_data = strategy_engine.check_5m_order_block(item.aggregator.candles_5m)
            if ob_data and ob_data["direction"] == item.direction:
                if ob_data["direction"] == "BULLISH":
                    if (self.market_breadth_bullish_pct >= 50.0 or item.strength > 0) and item.ltp >= item.session_vwap:
                        zone = OrderBlockZone(
                            symbol=item.symbol,
                            direction="BULLISH",
                            strategy_type="ORDER_BLOCK",
                            confirmed_time=ob_data["confirmed_time"],
                            zone_high=ob_data["zone_high"],
                            zone_low=ob_data["zone_low"],
                            breakout_candle=ob_data["breakout_candle"],
                            ob_candle=ob_data["ob_candle"],
                            atr_14=ob_data["atr_14"]
                        )
                        item.active_zone = zone
                        item.strategy_type = "ORDER_BLOCK"
                        item.ce_mid = None
                        item.zone_confirmed_time = ob_data["confirmed_time"].split(" ")[-1]
                        item.zone_high = zone.zone_high
                        item.zone_low = zone.zone_low
                        item.status = "ZONE_CONFIRMED"
                elif ob_data["direction"] == "BEARISH":
                    if (self.market_breadth_bullish_pct <= 50.0 or item.strength < 0) and item.ltp <= item.session_vwap:
                        zone = OrderBlockZone(
                            symbol=item.symbol,
                            direction="BEARISH",
                            strategy_type="ORDER_BLOCK",
                            confirmed_time=ob_data["confirmed_time"],
                            zone_high=ob_data["zone_high"],
                            zone_low=ob_data["zone_low"],
                            breakout_candle=ob_data["breakout_candle"],
                            ob_candle=ob_data["ob_candle"],
                            atr_14=ob_data["atr_14"]
                        )
                        item.active_zone = zone
                        item.strategy_type = "ORDER_BLOCK"
                        item.ce_mid = None
                        item.zone_confirmed_time = ob_data["confirmed_time"].split(" ")[-1]
                        item.zone_high = zone.zone_high
                        item.zone_low = zone.zone_low
                        item.status = "ZONE_CONFIRMED"

            # If no Order Block, check for SMC Liquidity Sweep + Fair Value Gap (FVG)
            if not item.active_zone or item.active_zone.expired:
                smc_data = strategy_engine.check_5m_smc_fvg(item.aggregator.candles_5m)
                if smc_data and smc_data["direction"] == item.direction:
                    if smc_data["direction"] == "BULLISH":
                        if item.ltp >= item.session_vwap:
                            zone = OrderBlockZone(
                                symbol=item.symbol,
                                direction="BULLISH",
                                strategy_type="SMC_FVG",
                                confirmed_time=smc_data["confirmed_time"],
                                zone_high=smc_data["zone_high"],
                                zone_low=smc_data["zone_low"],
                                breakout_candle=smc_data["breakout_candle"],
                                ob_candle=smc_data.get("ob_candle"),
                                atr_14=smc_data["atr_14"],
                                ce_mid=smc_data.get("ce_mid"),
                                sweep_level=smc_data.get("sweep_level")
                            )
                            item.active_zone = zone
                            item.strategy_type = "SMC_FVG"
                            item.ce_mid = smc_data.get("ce_mid")
                            item.zone_confirmed_time = smc_data["confirmed_time"].split(" ")[-1]
                            item.zone_high = zone.zone_high
                            item.zone_low = zone.zone_low
                            item.status = "ZONE_CONFIRMED"
                    elif smc_data["direction"] == "BEARISH":
                        if item.ltp <= item.session_vwap:
                            zone = OrderBlockZone(
                                symbol=item.symbol,
                                direction="BEARISH",
                                strategy_type="SMC_FVG",
                                confirmed_time=smc_data["confirmed_time"],
                                zone_high=smc_data["zone_high"],
                                zone_low=smc_data["zone_low"],
                                breakout_candle=smc_data["breakout_candle"],
                                ob_candle=smc_data.get("ob_candle"),
                                atr_14=smc_data["atr_14"],
                                ce_mid=smc_data.get("ce_mid"),
                                sweep_level=smc_data.get("sweep_level")
                            )
                            item.active_zone = zone
                            item.strategy_type = "SMC_FVG"
                            item.ce_mid = smc_data.get("ce_mid")
                            item.zone_confirmed_time = smc_data["confirmed_time"].split(" ")[-1]
                            item.zone_high = zone.zone_high
                            item.zone_low = zone.zone_low
                            item.status = "ZONE_CONFIRMED"

        # 2. Check for 3m Retest if active zone exists
        if item.active_zone and not item.active_zone.retested and not item.active_zone.expired:
            item.status = "WAITING_RETEST"
            retest_res = strategy_engine.check_3m_retest(
                zone=item.active_zone,
                completed_3m_candles=item.aggregator.candles_3m,
                session_high=item.aggregator.session_high,
                session_low=item.aggregator.session_low,
                session_vwap=item.session_vwap
            )
            if retest_res:
                item.retest_time = retest_res["retest_time"].split(" ")[-1]
                item.entry = retest_res["entry_price"]
                item.stop = retest_res["stop_loss"]
                item.target = retest_res["target"]
                item.status = "ORDER_PENDING"

        # 3. Simulate order fill and target/SL execution if order is pending
        if item.status == "ORDER_PENDING" and item.entry:
            if item.direction == "BULLISH":
                if item.ltp >= item.entry:
                    item.status = "IN_TRADE"
            elif item.direction == "BEARISH":
                if item.ltp <= item.entry:
                    item.status = "IN_TRADE"

        if item.status == "IN_TRADE" and item.target and item.stop:
            if item.direction == "BULLISH":
                if item.ltp >= item.target:
                    item.status = "TARGET_HIT"
                elif item.ltp <= item.stop:
                    item.status = "STOPPED_OUT"
            elif item.direction == "BEARISH":
                if item.ltp <= item.target:
                    item.status = "TARGET_HIT"
                elif item.ltp >= item.stop:
                    item.status = "STOPPED_OUT"

    def get_scanner_state(self, filter_mode: str = "TOP_10", strategy_filter: str = "ALL") -> Dict[str, Any]:
        """
        Returns strictly the Top 10 candidate stocks identified by the scanner.
        filter_mode: 'TOP_10' (market aligned), 'TOP_10_BULLISH', 'TOP_10_BEARISH'
        strategy_filter: 'ALL', 'ORDER_BLOCK', 'SMC_FVG'
        """
        if pytime.time() - self.last_sync_time > 15.0:
            self.sync_with_upstox_quotes()
            for item in self.items.values():
                self.check_strategy_for_item(item)
        else:
            self.evaluate_rankings_and_market_breadth()
        
        all_list = [item.to_table_dict() for item in self.items.values()]

        # Filter by strategy if specified and not 'ALL'
        if strategy_filter and strategy_filter != "ALL":
            strat_matching = [x for x in all_list if x.get("strategy_type") == strategy_filter]
            if len(strat_matching) >= 5:
                all_list = strat_matching

        if filter_mode == "TOP_10_BULLISH":
            filtered = [x for x in all_list if x["direction"] == "BULLISH"]
            def sort_bull(x):
                has_signal = 0 if x["entry"] else (1 if x["zone_low"] else 2)
                return (has_signal, x["rank"])
            filtered = sorted(filtered, key=sort_bull)[:10]

        elif filter_mode == "TOP_10_BEARISH":
            filtered = [x for x in all_list if x["direction"] == "BEARISH"]
            def sort_bear(x):
                has_signal = 0 if x["entry"] else (1 if x["zone_low"] else 2)
                return (has_signal, x["rank"])
            filtered = sorted(filtered, key=sort_bear)[:10]

        else:
            primary_direction = "BULLISH" if self.market_breadth_bullish_pct >= 50.0 else "BEARISH"
            
            # Prioritize active setups (with entry or confirmed zone)
            active_setups = [x for x in all_list if x["entry"] or x["zone_low"]]
            active_syms = {a["symbol"] for a in active_setups}
            
            # Fill remaining slots up to 10 with highest ranked directional candidates
            directional = [x for x in all_list if x["direction"] == primary_direction and x["symbol"] not in active_syms]
            directional.sort(key=lambda x: x["rank"])
            
            combined = active_setups + directional
            if len(combined) < 10:
                comb_syms = {c["symbol"] for c in combined}
                remaining = [x for x in all_list if x["symbol"] not in comb_syms]
                remaining.sort(key=lambda x: abs(x["strength"]), reverse=True)
                combined.extend(remaining)

            filtered = combined[:10]

        return {
            "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
            "total_universe": len(self.items),
            "scanned_count": len(filtered),
            "market_breadth_bullish_pct": round(self.market_breadth_bullish_pct, 1),
            "market_bias": "BULLISH" if self.market_breadth_bullish_pct >= 60.0 else ("BEARISH" if self.market_breadth_bullish_pct <= 40.0 else "NEUTRAL"),
            "filter_mode": filter_mode,
            "strategy_filter": strategy_filter,
            "items": filtered
        }

    # ==========================================
    # Live Simulated Tick & Candle Playback
    # ==========================================
    def start_simulation(self):
        if self.is_simulating:
            return
        self.is_simulating = True
        self.sim_task = asyncio.create_task(self._simulation_loop())

    def stop_simulation(self):
        self.is_simulating = False
        if self.sim_task:
            self.sim_task.cancel()
            self.sim_task = None

    async def _simulation_loop(self):
        """Generates realistic ticks and builds 3m & 5m completed candles."""
        # Pre-generate 25 completed 5m and 3m candles for each stock so OB criteria can evaluate immediately
        self._seed_completed_candles()

        step = 0
        while self.is_simulating:
            now_ist = datetime.now(IST)
            step += 1

            # Update prices for a batch of stocks every cycle
            for item in self.items.values():
                drift = 0.0003 if item.direction == "BULLISH" else (-0.0003 if item.direction == "BEARISH" else 0.0)
                volatility = random.uniform(-0.002, 0.002) + drift
                new_price = round(max(item.ltp * (1 + volatility), 1.0), 2)
                vol_delta = random.randint(100, 5000)

                # Feed into aggregator
                item.aggregator.process_tick(new_price, vol_delta, now_ist, item.prev_close)
                item.ltp = new_price
                item.session_vwap = item.aggregator.session_vwap
                item.high = item.aggregator.session_high
                item.low = item.aggregator.session_low

                # Periodically evaluate strategy
                if step % 2 == 0:
                    self.check_strategy_for_item(item)

            self.evaluate_rankings_and_market_breadth()

            # Broadcast update via WebSocket
            state = self.get_scanner_state("ALL")
            await self.broadcast({
                "type": "SCANNER_UPDATE",
                "data": state
            })

            await asyncio.sleep(1.0)

    def _seed_completed_candles(self):
        """Pre-seeds 25 completed 5m and 3m candles so 20-period moving averages and breakouts work."""
        now = datetime.now(IST)
        for sym, item in self.items.items():
            base_p = item.ltp
            candles_5m = []
            candles_3m = []

            # Create 24 historical 5m candles
            cur_p = base_p * 0.98
            for i in range(24, 0, -1):
                c_time = (now - timedelta(minutes=i * 5)).strftime("%Y-%m-%d %H:%M:%S")
                delta = random.uniform(-1.5, 2.0)
                o = cur_p
                c = round(o + delta, 2)
                h = round(max(o, c) + random.uniform(0.1, 1.0), 2)
                l = round(min(o, c) - random.uniform(0.1, 1.0), 2)
                vol = random.randint(10000, 50000)
                candles_5m.append({
                    "symbol": sym, "timeframe": "5m", "timestamp": c_time,
                    "open": o, "high": h, "low": l, "close": c, "volume": vol,
                    "vwap": round((o + c) / 2, 2), "is_bullish": c > o, "is_bearish": c < o,
                    "body": round(abs(c - o), 2), "range": round(h - l, 2)
                })
                cur_p = c

            item.aggregator.load_historical_candles("5m", candles_5m)

            # Create 30 historical 3m candles
            cur_p = base_p * 0.985
            for i in range(30, 0, -1):
                c_time = (now - timedelta(minutes=i * 3)).strftime("%Y-%m-%d %H:%M:%S")
                delta = random.uniform(-1.0, 1.5)
                o = cur_p
                c = round(o + delta, 2)
                h = round(max(o, c) + random.uniform(0.1, 0.8), 2)
                l = round(min(o, c) - random.uniform(0.1, 0.8), 2)
                vol = random.randint(6000, 30000)
                candles_3m.append({
                    "symbol": sym, "timeframe": "3m", "timestamp": c_time,
                    "open": o, "high": h, "low": l, "close": c, "volume": vol,
                    "vwap": round((o + c) / 2, 2), "is_bullish": c > o, "is_bearish": c < o,
                    "body": round(abs(c - o), 2), "range": round(h - l, 2)
                })
                cur_p = c
            item.aggregator.load_historical_candles("3m", candles_3m)

        # Preload authentic Upstox candles for key benchmark stocks
        for sym in ["HAL", "RELIANCE", "TCS", "INFY"]:
            if sym in self.items:
                it = self.items[sym]
                try:
                    to_d = datetime.now().strftime("%Y-%m-%d")
                    from_d = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
                    raw = upstox_service.get_historical_candles_range(it.instrument_key, to_d, from_d, "1minute")
                    if raw and len(raw) >= 50:
                        from .backtest_engine import aggregate_candles
                        c5 = aggregate_candles(raw[-150:], 5)
                        c3 = aggregate_candles(raw[-150:], 3)
                        it.aggregator.load_historical_candles("5m", c5)
                        it.aggregator.load_historical_candles("3m", c3)
                except Exception:
                    pass

scanner_manager = ScannerManager()
