import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  LineStyle,
} from "lightweight-charts";
import { X, ChevronLeft, ChevronRight, TrendingUp, TrendingDown } from "lucide-react";

const API_BASE = "http://localhost:8000";

// "2026-09-22 12:51:00" (IST wall clock) -> epoch seconds on the same "IST as UTC" axis the API uses
const toEpoch = (s) => (s ? Math.floor(Date.parse(s.replace(" ", "T").slice(0, 19) + "Z") / 1000) : null);

// Translucent rectangle between two times and two prices (lightweight-charts series primitive)
class ZoneRect {
  constructor({ t1, t2, high, low, fill, border }) {
    Object.assign(this, { t1, t2, high, low, fill, border });
    this._chart = null;
    this._series = null;
    const self = this;
    this._view = {
      zOrder: () => "bottom",
      renderer: () => ({
        draw(target) {
          if (!self._chart || !self._series) return;
          target.useBitmapCoordinateSpace(({ context, bitmapSize, horizontalPixelRatio: hpr, verticalPixelRatio: vpr }) => {
            const ts = self._chart.timeScale();
            const yH = self._series.priceToCoordinate(self.high);
            const yL = self._series.priceToCoordinate(self.low);
            if (yH === null || yL === null) return;
            const x1 = ts.timeToCoordinate(self.t1);
            const x2 = ts.timeToCoordinate(self.t2);
            const left = Math.round((x1 === null ? 0 : x1) * hpr);
            const right = Math.round((x2 === null ? bitmapSize.width / hpr : x2) * hpr);
            const top = Math.round(Math.min(yH, yL) * vpr);
            const h = Math.max(1, Math.round(Math.abs(yL - yH) * vpr));
            context.fillStyle = self.fill;
            context.fillRect(left, top, Math.max(1, right - left), h);
            context.strokeStyle = self.border;
            context.lineWidth = Math.max(1, Math.round(vpr));
            context.strokeRect(left + 0.5, top + 0.5, Math.max(1, right - left), h);
          });
        },
      }),
    };
  }
  attached({ chart, series }) {
    this._chart = chart;
    this._series = series;
  }
  detached() {
    this._chart = null;
    this._series = null;
  }
  updateAllViews() {}
  paneViews() {
    return [this._view];
  }
}

const REASON_LABEL = {
  TARGET_HIT: "🎯 Target hit",
  STOP_LOSS_HIT: "🛑 Stop loss hit",
  BREAKEVEN_STOP: "⚖️ Breakeven stop",
  EOD_1515_SQUAREOFF: "⏱️ 15:15 EOD square-off",
};

export default function BacktestTradeChartModal({ trades, index, onIndexChange, onClose }) {
  const trade = index !== null && index !== undefined ? trades[index] : null;
  const containerRef = useRef(null);
  const [timeframe, setTimeframe] = useState("3m");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const date = trade ? (trade.session_date || trade.entry_time?.slice(0, 10)) : null;
  const symbol = trade?.symbol;

  // Keyboard: Esc closes, arrows step through trades
  useEffect(() => {
    if (!trade) return;
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowLeft" && index > 0) onIndexChange(index - 1);
      else if (e.key === "ArrowRight" && index < trades.length - 1) onIndexChange(index + 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [trade, index, trades.length, onClose, onIndexChange]);

  // Fetch the session candles
  useEffect(() => {
    if (!symbol || !date) return;
    let alive = true;
    setLoading(true);
    setError(null);
    fetch(`${API_BASE}/api/backtest/trade-chart?symbol=${encodeURIComponent(symbol)}&date=${date}&timeframe=${timeframe}`)
      .then(async (r) => {
        if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => alive && setData(d))
      .catch((e) => alive && (setData(null), setError(e.message)))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [symbol, date, timeframe]);

  const times = useMemo(() => {
    if (!trade) return {};
    return {
      confirm: toEpoch(trade.confirmation_time),
      retest: toEpoch(trade.retest_time),
      entry: toEpoch(trade.entry_time),
      exit: toEpoch(trade.exit_time),
    };
  }, [trade]);

  // Draw
  useEffect(() => {
    if (!trade || !data || !data.candles?.length || !containerRef.current) return;
    const container = containerRef.current;
    const candles = data.candles;
    const step = data.step_seconds;

    const chart = createChart(container, {
      width: container.clientWidth || 900,
      height: 460,
      layout: { background: { color: "#0B0F19" }, textColor: "#94a3b8", fontSize: 12 },
      grid: { vertLines: { color: "#1e293b" }, horzLines: { color: "#1e293b" } },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: "#334155", scaleMargins: { top: 0.08, bottom: 0.22 } },
      timeScale: { borderColor: "#334155", timeVisible: true, secondsVisible: false },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981", downColor: "#f43f5e",
      borderUpColor: "#10b981", borderDownColor: "#f43f5e",
      wickUpColor: "#10b981", wickDownColor: "#f43f5e",
    });
    series.setData(candles.map(({ time, open, high, low, close }) => ({ time, open, high, low, close })));

    const vol = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "" });
    vol.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    vol.setData(candles.map((c) => ({
      time: c.time,
      value: c.volume,
      color: c.close >= c.open ? "rgba(16,185,129,0.35)" : "rgba(244,63,94,0.35)",
    })));

    const vwap = chart.addSeries(LineSeries, {
      color: "#a78bfa", lineWidth: 1, priceLineVisible: false, lastValueVisible: false, title: "VWAP",
    });
    vwap.setData(candles.map((c) => ({ time: c.time, value: c.vwap })));

    // Snap an arbitrary time to the bar that contains it
    const snap = (t) => {
      if (t === null || t === undefined) return null;
      let found = null;
      for (const c of candles) {
        if (c.time <= t) found = c.time;
        else break;
      }
      return found;
    };
    const sEntry = snap(times.entry);
    const sExit = snap(times.exit);
    const sConfirm = snap(times.confirm);
    const sRetest = snap(times.retest);

    const isLong = trade.direction === "BULLISH";
    const isSMC = trade.strategy === "SMC_FVG";
    const zoneColor = isSMC ? "168,85,247" : "234,179,8";

    // Zone box: from the confirmed setup until entry
    if (sConfirm && sEntry && trade.zone_high && trade.zone_low) {
      series.attachPrimitive(new ZoneRect({
        t1: sConfirm,
        t2: sExit || sEntry,
        high: trade.zone_high,
        low: trade.zone_low,
        fill: `rgba(${zoneColor},0.14)`,
        border: `rgba(${zoneColor},0.7)`,
      }));
    }

    const line = (price, color, title, style = LineStyle.Solid, width = 2) =>
      price && series.createPriceLine({ price, color, lineWidth: width, lineStyle: style, axisLabelVisible: true, title });
    line(trade.entry_price, "#06b6d4", "ENTRY");
    line(trade.stop_loss, "#f43f5e", "STOP");
    line(trade.target, "#10b981", "TARGET");
    line(trade.zone_high, `rgb(${zoneColor})`, isSMC ? "FVG HIGH" : "OB HIGH", LineStyle.Dashed, 1);
    line(trade.zone_low, `rgb(${zoneColor})`, isSMC ? "FVG LOW" : "OB LOW", LineStyle.Dashed, 1);
    if (isSMC && trade.ce_mid) line(trade.ce_mid, "#818cf8", "50% CE", LineStyle.Dotted, 1);

    // Entry -> exit path
    if (sEntry && sExit && sEntry !== sExit) {
      const path = chart.addSeries(LineSeries, {
        color: trade.pnl >= 0 ? "#34d399" : "#fb7185",
        lineWidth: 2, lineStyle: LineStyle.Dashed,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      });
      path.setData([
        { time: sEntry, value: trade.entry_price },
        { time: sExit, value: trade.exit_price },
      ]);
    }

    // Markers (must be sorted by time)
    const markers = [];
    if (sConfirm) markers.push({ time: sConfirm, position: isLong ? "belowBar" : "aboveBar", color: `rgb(${zoneColor})`, shape: "square", text: isSMC ? "FVG" : "OB" });
    if (sRetest && sRetest !== sConfirm) markers.push({ time: sRetest, position: isLong ? "belowBar" : "aboveBar", color: "#38bdf8", shape: "circle", text: "Retest" });
    if (sEntry) markers.push({ time: sEntry, position: isLong ? "belowBar" : "aboveBar", color: "#06b6d4", shape: isLong ? "arrowUp" : "arrowDown", text: `${isLong ? "BUY" : "SELL"} ${trade.entry_price}` });
    if (sExit) markers.push({ time: sExit, position: isLong ? "aboveBar" : "belowBar", color: trade.pnl >= 0 ? "#34d399" : "#fb7185", shape: isLong ? "arrowDown" : "arrowUp", text: `EXIT ${trade.exit_price}` });
    markers.sort((a, b) => a.time - b.time);
    createSeriesMarkers(series, markers);

    // Focus on the trade
    try {
      const from = (sConfirm || sEntry) - 45 * 60;
      const to = (sExit || sEntry) + 45 * 60;
      chart.timeScale().setVisibleRange({ from: Math.max(from, candles[0].time), to: Math.min(to, candles[candles.length - 1].time + step) });
    } catch {
      chart.timeScale().fitContent();
    }

    const onResize = () => chart.applyOptions({ width: container.clientWidth });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [data, trade, times]);

  if (!trade) return null;

  const isLong = trade.direction === "BULLISH";
  const win = trade.pnl >= 0;
  const fmt = (n) => (n === null || n === undefined ? "-" : Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md" onClick={onClose}>
      <div
        className="relative w-full max-w-6xl bg-[#0F172A] border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[94vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-xl border ${isLong ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-rose-500/10 text-rose-400 border-rose-500/20"}`}>
              {isLong ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-lg font-bold text-white">{trade.symbol}</h2>
                <span className="text-xs text-slate-400 font-mono">{date}</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${isLong ? "bg-emerald-500/20 text-emerald-300" : "bg-rose-500/20 text-rose-300"}`}>
                  {isLong ? "BUY" : "SELL"}
                </span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${trade.strategy === "SMC_FVG" ? "bg-purple-500/20 text-purple-300" : "bg-amber-500/20 text-amber-300"}`}>
                  {trade.strategy === "SMC_FVG" ? "⚡ SMC FVG" : "🧱 OB Retest"}
                </span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${win ? "bg-emerald-500/20 text-emerald-300" : "bg-rose-500/20 text-rose-300"}`}>
                  {win ? "WIN" : "LOSS"}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Trade {index + 1} of {trades.length} · use ← → to step, Esc to close
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center bg-slate-800/80 p-1 rounded-xl border border-slate-700/60">
              {["5m", "3m", "1m"].map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-3 py-1 text-xs font-semibold rounded-lg transition ${timeframe === tf ? "bg-cyan-500 text-slate-950" : "text-slate-400 hover:text-slate-200"}`}
                >
                  {tf}
                </button>
              ))}
            </div>
            <button disabled={index <= 0} onClick={() => onIndexChange(index - 1)} className="p-1.5 text-slate-300 hover:bg-slate-800 rounded-lg disabled:opacity-30">
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button disabled={index >= trades.length - 1} onClick={() => onIndexChange(index + 1)} className="p-1.5 text-slate-300 hover:bg-slate-800 rounded-lg disabled:opacity-30">
              <ChevronRight className="w-5 h-5" />
            </button>
            <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Stats strip */}
        <div className="px-5 py-2.5 grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-2 text-xs bg-slate-900/30 border-b border-slate-800/60 font-mono">
          {[
            ["Zone", `${fmt(trade.zone_low)} – ${fmt(trade.zone_high)}`, "text-amber-300"],
            ["Entry", `${fmt(trade.entry_price)} @ ${trade.entry_time?.slice(11, 16)}`, "text-cyan-300"],
            ["Stop", fmt(trade.stop_loss), "text-rose-400"],
            ["Target", fmt(trade.target), "text-emerald-400"],
            ["Exit", `${fmt(trade.exit_price)} @ ${trade.exit_time?.slice(11, 16)}`, "text-slate-200"],
            ["Qty", fmt(trade.shares), "text-slate-200"],
            ["Costs", trade.costs != null ? `₹${fmt(trade.costs)}` : "-", "text-slate-300"],
            ["Net PnL", `${win ? "+" : ""}₹${fmt(trade.pnl)}`, win ? "text-emerald-400" : "text-rose-400"],
            ["R multiple", trade.r_multiple != null ? `${trade.r_multiple}R` : "-", win ? "text-emerald-400" : "text-rose-400"],
          ].map(([label, value, cls]) => (
            <div key={label} className="bg-slate-800/40 p-2 rounded-lg border border-slate-700/40">
              <span className="block text-[10px] uppercase text-slate-400 font-sans font-semibold">{label}</span>
              <span className={`font-bold ${cls}`}>{value}</span>
            </div>
          ))}
        </div>

        {/* Chart */}
        <div className="relative bg-[#0B0F19] min-h-[460px]">
          {loading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#0B0F19]/80">
              <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-slate-400 mt-3">Fetching {timeframe} candles for {symbol} on {date}…</span>
            </div>
          )}
          {error && !loading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center text-sm text-rose-300 px-6 text-center">
              Could not load chart: {error}
            </div>
          )}
          <div ref={containerRef} className="w-full h-[460px]" />
        </div>

        {/* Legend */}
        <div className="px-5 py-2 bg-slate-900/80 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
          <div className="flex items-center gap-4 flex-wrap">
            <span><span className="inline-block w-2.5 h-2.5 rounded-sm bg-amber-400/60 mr-1.5" />Zone box</span>
            <span><span className="inline-block w-2.5 h-0.5 bg-cyan-400 mr-1.5 align-middle" />Entry</span>
            <span><span className="inline-block w-2.5 h-0.5 bg-rose-500 mr-1.5 align-middle" />Stop</span>
            <span><span className="inline-block w-2.5 h-0.5 bg-emerald-500 mr-1.5 align-middle" />Target</span>
            <span><span className="inline-block w-2.5 h-0.5 bg-violet-400 mr-1.5 align-middle" />Session VWAP</span>
          </div>
          <span>{REASON_LABEL[trade.exit_reason] || (trade.exit_reason?.startsWith("TARGET_HIT") ? REASON_LABEL.TARGET_HIT : trade.exit_reason)}</span>
        </div>
      </div>
    </div>
  );
}
