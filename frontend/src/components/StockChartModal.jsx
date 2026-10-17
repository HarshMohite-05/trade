import React, { useEffect, useRef, useState } from "react";
import { createChart, CandlestickSeries, HistogramSeries, LineStyle } from "lightweight-charts";
import { X, TrendingUp, TrendingDown, Target, ShieldAlert, Crosshair, BarChart3, Clock } from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function StockChartModal({ stock, isOpen, onClose }) {
  const chartContainerRef = useRef(null);
  const chartInstanceRef = useRef(null);
  const [timeframe, setTimeframe] = useState("5m");
  const [loading, setLoading] = useState(true);
  const [chartData, setChartData] = useState(null);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Fetch candle data when stock or timeframe changes
  useEffect(() => {
    if (!isOpen || !stock) return;

    let isMounted = true;
    setLoading(true);

    const fetchCandles = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/market/candles?symbol=${stock.symbol}&timeframe=${timeframe}`);
        const data = await res.json();
        if (isMounted) {
          setChartData(data);
          setLoading(false);
        }
      } catch (err) {
        console.error("Error fetching candles:", err);
        if (isMounted) setLoading(false);
      }
    };

    fetchCandles();
    return () => { isMounted = false; };
  }, [isOpen, stock, timeframe]);

  // Render Lightweight Chart v5
  useEffect(() => {
    if (!isOpen || !chartContainerRef.current || !chartData || !chartData.candles || chartData.candles.length === 0) return;

    // Remove existing chart instance
    if (chartInstanceRef.current) {
      try {
        chartInstanceRef.current.remove();
      } catch (e) {
        // ignore
      }
      chartInstanceRef.current = null;
    }

    const container = chartContainerRef.current;
    const width = container.clientWidth || 920;
    const height = 480;

    const chart = createChart(container, {
      width: width,
      height: height,
      layout: {
        background: { color: "#0B0F19" },
        textColor: "#94a3b8",
        fontSize: 12,
        fontFamily: "'Inter', sans-serif",
      },
      grid: {
        vertLines: { color: "#1e293b", style: 1 },
        horzLines: { color: "#1e293b", style: 1 },
      },
      crosshair: {
        mode: 1,
        vertLine: { color: "#64748b", width: 1, style: 2 },
        horzLine: { color: "#64748b", width: 1, style: 2 },
      },
      rightPriceScale: {
        borderColor: "#334155",
        scaleMargins: { top: 0.08, bottom: 0.22 },
      },
      timeScale: {
        borderColor: "#334155",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartInstanceRef.current = chart;

    // Add Candlestick Series (Lightweight-charts v5 syntax)
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#f43f5e",
      borderUpColor: "#10b981",
      borderDownColor: "#f43f5e",
      wickUpColor: "#10b981",
      wickDownColor: "#f43f5e",
    });

    candleSeries.setData(chartData.candles);

    // Add Volume Series (HistogramSeries in v5)
    try {
      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "",
      });

      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.82, bottom: 0 },
      });

      const volData = chartData.candles.map((c) => ({
        time: c.time,
        value: c.volume || 100,
        color: c.close >= c.open ? "rgba(16, 185, 129, 0.4)" : "rgba(244, 63, 94, 0.4)",
      }));
      volumeSeries.setData(volData);
    } catch (e) {
      console.warn("Volume series setup skipped:", e);
    }

    // Add Strategy Level Lines
    const levels = chartData.levels || stock;
    if (levels) {
      const entryVal = Number(levels.entry_price || levels.entry);
      const stopVal = Number(levels.stop_loss || levels.stop);
      const targetVal = Number(levels.target);
      const zHigh = Number(levels.zone_high);
      const zLow = Number(levels.zone_low);

      if (entryVal && !isNaN(entryVal)) {
        candleSeries.createPriceLine({
          price: entryVal,
          color: "#06b6d4",
          lineWidth: 2,
          lineStyle: LineStyle.Solid,
          axisLabelVisible: true,
          title: "ENTRY TRIGGER",
        });
      }

      if (stopVal && !isNaN(stopVal)) {
        candleSeries.createPriceLine({
          price: stopVal,
          color: "#f43f5e",
          lineWidth: 2,
          lineStyle: LineStyle.Solid,
          axisLabelVisible: true,
          title: "STOP LOSS",
        });
      }

      const isSMC = (levels.strategy_type === "SMC_FVG") || (stock.strategy_type === "SMC_FVG");
      const zoneColor = isSMC ? "#a855f7" : "#eab308";
      const zoneHighLabel = isSMC ? "FVG HIGH" : "OB HIGH";
      const zoneLowLabel = isSMC ? "FVG LOW" : "OB LOW";

      if (targetVal && !isNaN(targetVal)) {
        candleSeries.createPriceLine({
          price: targetVal,
          color: "#10b981",
          lineWidth: 2,
          lineStyle: LineStyle.Solid,
          axisLabelVisible: true,
          title: "TARGET (2R)",
        });
      }

      if (zHigh && !isNaN(zHigh)) {
        candleSeries.createPriceLine({
          price: zHigh,
          color: zoneColor,
          lineWidth: 1.5,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: zoneHighLabel,
        });
      }

      // If SMC, draw 50% Consequent Encroachment (C.E.) line
      const ceVal = Number(levels.ce_mid || stock.ce_mid);
      if (isSMC && ceVal && !isNaN(ceVal)) {
        candleSeries.createPriceLine({
          price: ceVal,
          color: "#818cf8",
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          axisLabelVisible: true,
          title: "50% C.E.",
        });
      }

      if (zLow && !isNaN(zLow)) {
        candleSeries.createPriceLine({
          price: zLow,
          color: zoneColor,
          lineWidth: 1.5,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: zoneLowLabel,
        });
      }
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (container && chartInstanceRef.current) {
        chartInstanceRef.current.applyOptions({ width: container.clientWidth });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (chartInstanceRef.current) {
        try {
          chartInstanceRef.current.remove();
        } catch (e) {
          // ignore
        }
        chartInstanceRef.current = null;
      }
    };
  }, [isOpen, chartData]);

  if (!isOpen || !stock) return null;

  const isBull = stock.direction === "BULLISH";
  const isSMC = stock.strategy_type === "SMC_FVG" || (chartData?.levels?.strategy_type === "SMC_FVG");
  const levels = chartData?.levels || stock;
  const entryVal = levels.entry_price || levels.entry;
  const stopVal = levels.stop_loss || levels.stop;
  const targetVal = levels.target;
  const riskPerShare = (entryVal && stopVal) ? Math.abs(entryVal - stopVal).toFixed(2) : null;
  const recommendedShares = riskPerShare ? Math.max(1, Math.floor(2500 / parseFloat(riskPerShare))) : null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn"
      onClick={onClose}
    >
      <div 
        className="relative w-full max-w-5xl bg-[#0F172A] border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-4">
            <div className={`p-2 rounded-xl ${isBull ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-rose-500/10 text-rose-400 border border-rose-500/20"}`}>
              {isBull ? <TrendingUp className="w-6 h-6" /> : <TrendingDown className="w-6 h-6" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-white tracking-wide">{stock.symbol}</h2>
                <span className="text-xs px-2 py-0.5 rounded font-medium bg-slate-800 text-slate-300 border border-slate-700">
                  {stock.sector || "F&O"}
                </span>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase ${isBull ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : "bg-rose-500/20 text-rose-300 border border-rose-500/30"}`}>
                  {stock.direction} (Rank #{stock.rank})
                </span>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold tracking-wide uppercase ${isSMC ? "bg-purple-500/20 text-purple-300 border border-purple-500/30" : "bg-amber-500/20 text-amber-300 border border-amber-500/30"}`}>
                  {isSMC ? "⚡ SMC Liquidity FVG" : "🧱 Order Block Retest"}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                LTP: <span className="font-semibold text-slate-200">₹{stock.ltp}</span> • VWAP: <span className="font-semibold text-slate-200">₹{stock.vwap}</span> • 24h Change: <span className={`font-semibold ${stock.pct_change >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{stock.pct_change > 0 ? "+" : ""}{stock.pct_change}%</span>
              </p>
            </div>
          </div>

          {/* Timeframe Buttons & Close */}
          <div className="flex items-center gap-3">
            <div className="flex items-center bg-slate-800/80 p-1 rounded-xl border border-slate-700/60">
              {["5m", "3m", "1m"].map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${timeframe === tf ? "bg-cyan-500 text-slate-950 shadow-md" : "text-slate-400 hover:text-slate-200"}`}
                >
                  {tf === "5m" ? "5m (Setup)" : tf === "3m" ? "3m (Retest)" : "1m (Exec)"}
                </button>
              ))}
            </div>

            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Strategy Badges Strip */}
        <div className="px-6 py-2.5 bg-slate-900/30 border-b border-slate-800/60 grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
          <div className="bg-slate-800/40 p-2 rounded-lg border border-slate-700/40">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">
              {isSMC ? "SMC FVG Imbalance Zone" : "5m Order Block Zone"}
            </span>
            <span className={`font-bold ${isSMC ? "text-purple-400" : "text-amber-400"}`}>
              {levels.zone_high && levels.zone_low ? `₹${levels.zone_low} - ₹${levels.zone_high}` : (stock.zone || "-")}
            </span>
            {isSMC && (levels.ce_mid || stock.ce_mid) && (
              <span className="block text-[9px] text-indigo-300 font-mono">
                50% C.E.: ₹{levels.ce_mid || stock.ce_mid}
              </span>
            )}
          </div>

          <div className="bg-slate-800/40 p-2 rounded-lg border border-slate-700/40">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold flex items-center gap-1">
              <Crosshair className="w-3 h-3 text-cyan-400" /> Entry Trigger
            </span>
            <span className="font-bold text-cyan-300">
              {entryVal ? `₹${entryVal}` : "-"}
            </span>
          </div>

          <div className="bg-slate-800/40 p-2 rounded-lg border border-slate-700/40">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold flex items-center gap-1">
              <ShieldAlert className="w-3 h-3 text-rose-400" /> Stop Loss
            </span>
            <span className="font-bold text-rose-400">
              {stopVal ? `₹${stopVal}` : "-"}
            </span>
          </div>

          <div className="bg-slate-800/40 p-2 rounded-lg border border-slate-700/40">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold flex items-center gap-1">
              <Target className="w-3 h-3 text-emerald-400" /> 2R Target
            </span>
            <span className="font-bold text-emerald-400">
              {targetVal ? `₹${targetVal}` : "-"}
            </span>
          </div>

          <div className="bg-slate-800/40 p-2 rounded-lg border border-slate-700/40">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold flex items-center gap-1">
              <BarChart3 className="w-3 h-3 text-indigo-400" /> Position Size
            </span>
            <span className="font-bold text-indigo-300">
              {recommendedShares ? `${recommendedShares} shares (₹2.5k risk)` : "0.5% risk"}
            </span>
          </div>
        </div>

        {/* Chart Canvas Area */}
        <div className="relative flex-1 min-h-[460px] bg-[#0B0F19]">
          {loading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#0B0F19]/80 backdrop-blur-sm">
              <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-xs text-slate-400 mt-3 font-medium">Fetching authentic Upstox {timeframe} candles...</span>
            </div>
          )}
          <div ref={chartContainerRef} className="w-full h-[480px]" />
        </div>

        {/* Footer Info */}
        <div className="px-6 py-2.5 bg-slate-900/80 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 inline-block"></span>
              Cyan: 1-Tick Entry Trigger
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block"></span>
              Red: Stop Loss (Zone ± 0.10 ATR)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span>
              Green: 2R Target
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 inline-block"></span>
              Yellow: 5m Order Block Boundaries
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-slate-400 font-mono text-[11px]">
            <Clock className="w-3.5 h-3.5" />
            Window: 09:45 – 14:30 IST | Square-Off: 15:15 IST
          </div>
        </div>
      </div>
    </div>
  );
}
