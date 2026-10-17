import React, { useState, useEffect, useRef } from 'react';
import { 
  Key, ShieldCheck, RefreshCw, Radio, CheckCircle2, 
  AlertCircle, ExternalLink, Activity, ArrowUpRight, 
  ArrowDownRight, LogOut, Terminal, Layers, Play,
  TrendingUp, TrendingDown, Clock, Search, Filter,
  DollarSign, BarChart2, BarChart3, Check, X, Eye, Zap, Square, Target, ShieldAlert, Crosshair
} from 'lucide-react';
import StockChartModal from './components/StockChartModal';
import BacktestTradeChartModal from './components/BacktestTradeChartModal';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const WS_BASE = import.meta.env.VITE_WS_BASE_URL || (API_BASE.replace(/^http/, 'ws') + '/api/scanner/ws');

export default function App() {
  const [activeTab, setActiveTab] = useState('scanner');
  const [chartModalStock, setChartModalStock] = useState(null);
  
  // ==========================================
  // Auth State
  // ==========================================
  const [authStatus, setAuthStatus] = useState({
    authenticated: false,
    api_key: '',
    redirect_uri: `${API_BASE}/api/auth/callback`,
    token_preview: null,
    user_name: null,
    user_id: null,
  });
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [redirectUri, setRedirectUri] = useState(`${API_BASE}/api/auth/callback`);
  const [manualToken, setManualToken] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [authMessage, setAuthMessage] = useState(null);

  // Reliance Tick Test
  const [tickLoading, setTickLoading] = useState(false);
  const [tickData, setTickData] = useState(null);
  const [tickError, setTickError] = useState(null);

  // ==========================================
  // Top 10 Scanned Stocks State
  // ==========================================
  const [top10Items, setTop10Items] = useState([]);
  const [marketBreadth, setMarketBreadth] = useState(50);
  const [marketBias, setMarketBias] = useState('NEUTRAL');
  const [totalEvaluated, setTotalEvaluated] = useState(60);
  const [scannerFilter, setScannerFilter] = useState('TOP_10'); // 'TOP_10', 'TOP_10_BULLISH', 'TOP_10_BEARISH'
  const [strategyMode, setStrategyMode] = useState('ALL'); // 'ALL', 'ORDER_BLOCK', 'SMC_FVG'
  const [isSimulating, setIsSimulating] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [lastScannedTime, setLastScannedTime] = useState('');
  const wsRef = useRef(null);

  // ==========================================
  // Backtester State
  // ==========================================
  const [availableStocks, setAvailableStocks] = useState([]);
  const [backtestSymbol, setBacktestSymbol] = useState('ALL');
  const [backtestStrategy, setBacktestStrategy] = useState('ALL'); // 'ALL', 'ORDER_BLOCK', 'SMC_FVG'
  const [dateFrom, setDateFrom] = useState('2026-10-01');
  const [dateTo, setDateTo] = useState('2026-10-17');
  const [initialCapital, setInitialCapital] = useState(500000);
  const [riskPct, setRiskPct] = useState(0.5);
  const [backtestLoading, setBacktestLoading] = useState(false);
  const [backtestResult, setBacktestResult] = useState(null);
  const [backtestHistory, setBacktestHistory] = useState([]);
  const [tradeFilter, setTradeFilter] = useState('ALL');
  const [chartTradeIdx, setChartTradeIdx] = useState(null);
  const [backtestError, setBacktestError] = useState('');

  // IST Clock
  const [istTime, setIstTime] = useState('');

  // ==========================================
  // Lifecycle & WebSocket
  // ==========================================
  useEffect(() => {
    fetchAuthStatus();
    fetchScannerTop10(scannerFilter, strategyMode);
    fetchBacktestStocks();
    fetchBacktestHistory();

    const timer = setInterval(() => {
      const now = new Date();
      setIstTime(now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false }) + ' IST');
    }, 1000);

    connectScannerWebSocket();

    return () => {
      clearInterval(timer);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  useEffect(() => {
    fetchScannerTop10(scannerFilter, strategyMode);
  }, [scannerFilter, strategyMode]);

  const connectScannerWebSocket = () => {
    try {
      const ws = new WebSocket(WS_BASE);
      wsRef.current = ws;

      ws.onopen = () => setWsConnected(true);

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'INITIAL_STATE' || msg.type === 'SCANNER_UPDATE') {
            const data = msg.data;
            if (data.items) setTop10Items(data.items.slice(0, 10));
            if (data.market_breadth_bullish_pct !== undefined) setMarketBreadth(data.market_breadth_bullish_pct);
            if (data.market_bias) setMarketBias(data.market_bias);
            if (data.total_universe) setTotalEvaluated(data.total_universe);
            if (data.timestamp) setLastScannedTime(data.timestamp);
          }
        } catch (err) {
          console.error('WS Parse Error', err);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        setTimeout(connectScannerWebSocket, 3000);
      };

      ws.onerror = () => setWsConnected(false);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchScannerTop10 = async (filter = 'TOP_10', strat = strategyMode) => {
    try {
      const res = await fetch(`${API_BASE}/api/scanner/state?filter=${filter}&strategy=${strat}`);
      const data = await res.json();
      if (data.items) setTop10Items(data.items.slice(0, 10));
      if (data.market_breadth_bullish_pct !== undefined) setMarketBreadth(data.market_breadth_bullish_pct);
      if (data.market_bias) setMarketBias(data.market_bias);
      if (data.total_universe) setTotalEvaluated(data.total_universe);
      if (data.timestamp) setLastScannedTime(data.timestamp);
    } catch (err) {
      console.error(err);
    }
  };

  const handleScanNow = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/scanner/scan-now?filter=${scannerFilter}&strategy=${strategyMode}`, { method: 'POST' });
      const data = await res.json();
      if (data.state && data.state.items) {
        setTop10Items(data.state.items.slice(0, 10));
        setMarketBreadth(data.state.market_breadth_bullish_pct);
        setMarketBias(data.state.market_bias);
        setLastScannedTime(data.state.timestamp);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleSimulation = async () => {
    try {
      if (isSimulating) {
        await fetch(`${API_BASE}/api/scanner/simulation/stop`, { method: 'POST' });
        setIsSimulating(false);
      } else {
        await fetch(`${API_BASE}/api/scanner/simulation/start`, { method: 'POST' });
        setIsSimulating(true);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchAuthStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/status`);
      const data = await res.json();
      setAuthStatus(data);
      if (data.api_key) setApiKey(data.api_key);
      if (data.redirect_uri) setRedirectUri(data.redirect_uri);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchBacktestStocks = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/backtest/stocks`);
      const data = await res.json();
      setAvailableStocks(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchBacktestHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/backtest/history`);
      const data = await res.json();
      setBacktestHistory(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRunBacktest = async (e) => {
    e.preventDefault();
    setBacktestLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/backtest/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbols: [backtestSymbol],
          date_from: dateFrom,
          date_to: dateTo,
          initial_capital: Number(initialCapital),
          risk_per_trade_pct: Number(riskPct),
          strategy: backtestStrategy,
        })
      });
      const data = await res.json();
      if (!res.ok || !data.summary) throw new Error(data.detail || `Backtest failed (HTTP ${res.status})`);
      setBacktestError('');
      setChartTradeIdx(null);
      setBacktestResult(data);
      fetchBacktestHistory();
    } catch (err) {
      console.error(err);
      setBacktestError(String(err.message || err));
    } finally {
      setBacktestLoading(false);
    }
  };

  const handleSelectHistoryRun = async (runId) => {
    try {
      const res = await fetch(`${API_BASE}/api/backtest/run/${runId}/trades`);
      const trades = await res.json();
      const runItem = backtestHistory.find(r => r.id === runId);
      if (runItem) {
        setChartTradeIdx(null);
        setBacktestResult({
          summary: runItem,
          trades: trades,
          equity_curve: []
        });
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveCredentials = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthMessage(null);
    try {
      const res = await fetch(`${API_BASE}/api/auth/credentials`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey, api_secret: apiSecret, redirect_uri: redirectUri })
      });
      const data = await res.json();
      if (res.ok) {
        setAuthMessage({ type: 'success', text: 'Credentials saved! You can now log in with Upstox.' });
        fetchAuthStatus();
      } else {
        setAuthMessage({ type: 'error', text: data.detail || 'Failed to save credentials' });
      }
    } catch (err) {
      setAuthMessage({ type: 'error', text: 'Backend connection failed' });
    } finally {
      setAuthLoading(false);
    }
  };

  const handleManualTokenSubmit = async (e) => {
    e.preventDefault();
    if (!manualToken.trim()) return;
    setAuthLoading(true);
    setAuthMessage(null);
    try {
      const res = await fetch(`${API_BASE}/api/auth/manual-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: manualToken, api_key: apiKey, api_secret: apiSecret })
      });
      const data = await res.json();
      if (res.ok && data.status !== 'error') {
        setAuthMessage({ type: 'success', text: data.message || 'Token configured successfully!' });
        setManualToken('');
        fetchAuthStatus();
      } else {
        setAuthMessage({ type: 'error', text: data.message || data.detail || 'Invalid token' });
      }
    } catch (err) {
      setAuthMessage({ type: 'error', text: 'Server error' });
    } finally {
      setAuthLoading(false);
    }
  };

  const handlePullRelianceTick = async () => {
    setTickLoading(true);
    setTickError(null);
    try {
      const res = await fetch(`${API_BASE}/api/market/tick?instrument_key=NSE_EQ|INE002A01018`);
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        const raw = data.data;
        const relianceKey = Object.keys(raw).find(k => k.includes('RELIANCE') || k.includes('INE002A01018')) || Object.keys(raw)[0];
        setTickData(raw[relianceKey]);
      } else {
        setTickError(data.detail || data.message || 'Failed to pull live tick');
      }
    } catch (err) {
      setTickError('Failed to communicate with FastAPI backend');
    } finally {
      setTickLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-900 text-slate-100 flex flex-col font-sans selection:bg-brand-500 selection:text-white">
      {/* Top Navbar */}
      <header className="border-b border-dark-700 bg-dark-850 sticky top-0 z-50 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-brand-600 to-blue-400 flex items-center justify-center shadow-lg shadow-brand-500/20">
            <Target className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-bold text-lg tracking-tight text-white">ORDER BLOCK SCANNER</h1>
              <span className="px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded-full bg-emerald-500/10 text-bull-light border border-emerald-500/30">
                Signals & Setups Identification
              </span>
            </div>
            <p className="text-xs text-slate-400">Order Block First Retest • Entry Price & Time Identifier</p>
          </div>
        </div>

        {/* Center Tabs */}
        <div className="flex items-center space-x-1 bg-dark-800 p-1 rounded-xl border border-dark-700">
          <button
            onClick={() => setActiveTab('scanner')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-2 transition-all ${
              activeTab === 'scanner'
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-dark-700'
            }`}
          >
            <Radio className="h-3.5 w-3.5" />
            <span>Top 10 Scanned Stocks</span>
          </button>
          <button
            onClick={() => setActiveTab('backtest')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-2 transition-all ${
              activeTab === 'backtest'
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-dark-700'
            }`}
          >
            <BarChart2 className="h-3.5 w-3.5" />
            <span>Backtester (Historical Signals)</span>
          </button>
          <button
            onClick={() => setActiveTab('auth')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-2 transition-all ${
              activeTab === 'auth'
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-dark-700'
            }`}
          >
            <Key className="h-3.5 w-3.5" />
            <span>Upstox API</span>
          </button>
        </div>

        {/* Right Status */}
        <div className="flex items-center space-x-3">
          <div className="px-3 py-1 bg-dark-800 rounded-lg border border-dark-700 text-xs font-mono text-slate-300">
            {istTime || '15:20:00 IST'}
          </div>

          <div className="flex items-center space-x-2 px-3 py-1 rounded-lg border text-xs font-medium bg-dark-800 border-dark-700">
            <span className={`h-2 w-2 rounded-full ${wsConnected ? 'bg-bull animate-pulse' : 'bg-bear'}`} />
            <span className={wsConnected ? 'text-bull-light' : 'text-slate-400'}>
              {wsConnected ? 'Live Feed' : 'Connecting'}
            </span>
          </div>

          <div className="flex items-center space-x-2 px-3 py-1 rounded-lg border text-xs font-medium bg-dark-800 border-dark-700">
            <span className={`h-2 w-2 rounded-full ${authStatus.authenticated ? 'bg-bull' : 'bg-amber-400'}`} />
            <span className={authStatus.authenticated ? 'text-bull-light' : 'text-slate-400'}>
              {authStatus.authenticated ? (authStatus.user_name || authStatus.user_id || 'Connected') : 'No Token'}
            </span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-[1500px] w-full mx-auto p-6 space-y-6">

        {/* ========================================================= */}
        {/* TAB 1: TOP 10 SCANNED STOCKS (IDENTIFIER ONLY)            */}
        {/* ========================================================= */}
        {activeTab === 'scanner' && (
          <div className="space-y-6">
            {/* Disclaimer Banner: Identification Only */}
            <div className="p-3.5 rounded-xl bg-brand-500/10 border border-brand-500/20 text-xs text-blue-300 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <ShieldAlert className="h-4 w-4 text-brand-400 flex-shrink-0" />
                <span>
                  <strong>Setup Identification Mode:</strong> The scanner scans {totalEvaluated} F&O universe stocks and pinpoints strictly the <strong>Top 10 Scanned Stocks</strong> with their exact <strong>Entry Price, Entry Time, Zone, Stop Loss, and Target</strong>. No automated orders are sent to the broker.
                </span>
              </div>
              <span className="text-[11px] font-mono text-slate-400 ml-4 flex-shrink-0">
                Last Evaluated: {lastScannedTime.split(' ')[1] || 'Just now'}
              </span>
            </div>

            {/* Top Toolbar: Filters, Strategy Selector, Market Breadth, Scan Now */}
            <div className="glass-panel p-4 rounded-2xl flex flex-col xl:flex-row xl:items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-3">
                {/* Directional Toggle */}
                <div className="flex items-center space-x-1.5 bg-dark-850 p-1 rounded-xl border border-dark-700">
                  <span className="text-[11px] text-slate-400 px-2 font-medium">Filter:</span>
                  <button
                    onClick={() => setScannerFilter('TOP_10')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition ${
                      scannerFilter === 'TOP_10'
                        ? 'bg-brand-600 text-white shadow-md'
                        : 'text-slate-300 hover:bg-dark-700'
                    }`}
                  >
                    Aligned ({top10Items.length})
                  </button>
                  <button
                    onClick={() => setScannerFilter('TOP_10_BULLISH')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold flex items-center space-x-1 transition ${
                      scannerFilter === 'TOP_10_BULLISH'
                        ? 'bg-bull text-white shadow-lg shadow-bull/20'
                        : 'text-bull-light hover:bg-dark-700'
                    }`}
                  >
                    <TrendingUp className="h-3.5 w-3.5" />
                    <span>Bullish</span>
                  </button>
                  <button
                    onClick={() => setScannerFilter('TOP_10_BEARISH')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold flex items-center space-x-1 transition ${
                      scannerFilter === 'TOP_10_BEARISH'
                        ? 'bg-bear text-white shadow-lg shadow-bear/20'
                        : 'text-bear-light hover:bg-dark-700'
                    }`}
                  >
                    <TrendingDown className="h-3.5 w-3.5" />
                    <span>Bearish</span>
                  </button>
                </div>

                {/* Strategy Selector Toggle */}
                <div className="flex items-center space-x-1 bg-dark-850 p-1 rounded-xl border border-dark-700">
                  <span className="text-[11px] text-slate-400 px-2 font-medium">Strategy:</span>
                  <button
                    onClick={() => setStrategyMode('ALL')}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                      strategyMode === 'ALL'
                        ? 'bg-brand-600 text-white shadow'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    ✨ All (SMC+OB)
                  </button>
                  <button
                    onClick={() => setStrategyMode('SMC_FVG')}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition flex items-center space-x-1 ${
                      strategyMode === 'SMC_FVG'
                        ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
                        : 'text-purple-300 hover:bg-dark-700'
                    }`}
                  >
                    <span>⚡ SMC FVG</span>
                  </button>
                  <button
                    onClick={() => setStrategyMode('ORDER_BLOCK')}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition flex items-center space-x-1 ${
                      strategyMode === 'ORDER_BLOCK'
                        ? 'bg-amber-600 text-white shadow-lg shadow-amber-600/30'
                        : 'text-amber-300 hover:bg-dark-700'
                    }`}
                  >
                    <span>🧱 OB Retest</span>
                  </button>
                </div>
              </div>

              {/* Market Breadth Indicator */}
              <div className="flex items-center space-x-3 bg-dark-800 px-4 py-2 rounded-xl border border-dark-700">
                <span className="text-xs text-slate-400">Market Breadth:</span>
                <div className="flex items-center space-x-2">
                  <div className="w-24 bg-dark-900 rounded-full h-2 overflow-hidden border border-dark-700">
                    <div
                      className="bg-bull h-full transition-all duration-500"
                      style={{ width: `${marketBreadth}%` }}
                    />
                  </div>
                  <span className={`text-xs font-mono font-bold ${
                    marketBreadth >= 60 ? 'text-bull' : marketBreadth <= 40 ? 'text-bear' : 'text-slate-300'
                  }`}>
                    {marketBreadth}%
                  </span>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  marketBias === 'BULLISH' ? 'bg-bull/20 text-bull-light' : marketBias === 'BEARISH' ? 'bg-bear/20 text-bear-light' : 'bg-dark-700 text-slate-400'
                }`}>
                  {marketBias} BIAS
                </span>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={handleScanNow}
                  className="px-3.5 py-2 bg-dark-750 hover:bg-dark-700 text-slate-200 text-xs font-medium rounded-xl flex items-center space-x-1.5 border border-dark-600 transition"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  <span>Scan Now</span>
                </button>

                <button
                  onClick={handleToggleSimulation}
                  className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center space-x-2 transition shadow-lg ${
                    isSimulating
                      ? 'bg-bear hover:bg-bear-light text-white shadow-bear/20'
                      : 'bg-brand-600 hover:bg-brand-500 text-white shadow-brand-500/20'
                  }`}
                >
                  {isSimulating ? (
                    <>
                      <Square className="h-3.5 w-3.5 fill-current" />
                      <span>Stop Simulation</span>
                    </>
                  ) : (
                    <>
                      <Play className="h-3.5 w-3.5 fill-current" />
                      <span>Live Simulation (Demo)</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Top 10 Scanned Candidate Stocks Table */}
            <div className="glass-panel rounded-2xl overflow-hidden border border-dark-700">
              <div className="p-4 bg-dark-850 border-b border-dark-700 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                    Top 10 Scanned Stocks — Entry Signals & Price Targets
                  </h2>
                </div>
                <span className="text-xs text-slate-400 font-mono">
                  Displaying strictly 10 candidate setups
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-dark-800/90 border-b border-dark-700 text-slate-400 font-mono text-[11px] uppercase tracking-wider">
                      <th className="py-3 px-4">Rank / Stock</th>
                      <th className="py-3 px-3">Strategy</th>
                      <th className="py-3 px-3">Direction</th>
                      <th className="py-3 px-3">Strength Score</th>
                      <th className="py-3 px-3">LTP / VWAP</th>
                      <th className="py-3 px-3">First Radar Time</th>
                      <th className="py-3 px-3">Zone Confirmed Time</th>
                      <th className="py-3 px-3">Zone (Low - High)</th>
                      <th className="py-3 px-3 bg-brand-500/5 text-brand-300 font-bold">Signal / Entry Time</th>
                      <th className="py-3 px-3 bg-brand-500/10 text-white font-bold">Exact Entry Price</th>
                      <th className="py-3 px-3">Stop Loss</th>
                      <th className="py-3 px-3">Target</th>
                      <th className="py-3 px-4">Setup Status</th>
                      <th className="py-3 px-4 text-right">Chart & Levels</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dark-700/60 font-mono">
                    {top10Items.length === 0 ? (
                      <tr>
                        <td colSpan={14} className="py-12 text-center text-slate-400 font-sans">
                          Evaluating scanner candidates... Click "Scan Now" or "Live Simulation" above.
                        </td>
                      </tr>
                    ) : (
                      top10Items.map((item, idx) => {
                        const isBull = item.direction === 'BULLISH';
                        const isBear = item.direction === 'BEARISH';
                        const hasEntry = Boolean(item.entry);
                        const hasZone = Boolean(item.zone_low && item.zone_high);

                        let statusBadge = 'bg-dark-750 text-slate-400 border-dark-600';
                        if (item.entry) {
                          statusBadge = isBull 
                            ? 'bg-bull text-white font-bold shadow-lg shadow-bull/20' 
                            : 'bg-bear text-white font-bold shadow-lg shadow-bear/20';
                        } else if (item.status === 'ZONE_CONFIRMED') {
                          statusBadge = 'bg-blue-500/20 text-brand-400 border-brand-500/40 animate-pulse font-semibold';
                        } else if (item.status === 'WAITING_RETEST') {
                          statusBadge = 'bg-amber-500/20 text-amber-300 border-amber-500/40 font-semibold';
                        } else {
                          statusBadge = 'bg-dark-700 text-slate-300 border-dark-600';
                        }

                        return (
                          <tr
                            key={item.symbol}
                            onClick={() => setSelectedStock(item)}
                            className="hover:bg-dark-750/80 cursor-pointer transition"
                          >
                            {/* Rank & Stock */}
                            <td className="py-3.5 px-4">
                              <div className="flex items-center space-x-2">
                                <span className="text-slate-500 font-bold text-xs">#{idx + 1}</span>
                                <div>
                                  <div className="font-bold text-slate-100 flex items-center space-x-1.5">
                                    <span>{item.symbol}</span>
                                    <span className="text-[10px] text-slate-500 font-sans font-normal">({item.sector})</span>
                                  </div>
                                  <div className="text-[10px] text-slate-400 font-sans truncate max-w-[130px]">
                                    {item.name}
                                  </div>
                                </div>
                              </div>
                            </td>

                            {/* Strategy Type */}
                            <td className="py-3.5 px-3">
                              {item.strategy_type === 'SMC_FVG' ? (
                                <div className="space-y-0.5">
                                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30 inline-flex items-center space-x-1">
                                    <span>⚡ SMC FVG</span>
                                  </span>
                                  {item.ce_mid && (
                                    <div className="text-[9px] text-indigo-300 font-mono">
                                      50% CE: ₹{item.ce_mid}
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30 inline-flex items-center space-x-1">
                                  <span>🧱 OB Retest</span>
                                </span>
                              )}
                            </td>

                            {/* Direction */}
                            <td className="py-3.5 px-3">
                              {isBull ? (
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-bull/15 text-bull-light border border-bull/30 flex items-center w-fit space-x-1">
                                  <ArrowUpRight className="h-3 w-3" />
                                  <span>BUY / LONG</span>
                                </span>
                              ) : isBear ? (
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-bear/15 text-bear-light border border-bear/30 flex items-center w-fit space-x-1">
                                  <ArrowDownRight className="h-3 w-3" />
                                  <span>SELL / SHORT</span>
                                </span>
                              ) : (
                                <span className="text-slate-500 text-[11px]">NEUTRAL</span>
                              )}
                            </td>

                            {/* Strength */}
                            <td className="py-3.5 px-3">
                              <span className={`font-semibold ${item.strength > 0 ? 'text-bull' : item.strength < 0 ? 'text-bear' : 'text-slate-400'}`}>
                                {item.strength > 0 ? `+${item.strength}` : item.strength}
                              </span>
                              <div className="text-[10px] text-slate-500">
                                {item.pct_change > 0 ? `+${item.pct_change}%` : `${item.pct_change}%`}
                              </div>
                            </td>

                            {/* LTP / VWAP */}
                            <td className="py-3.5 px-3">
                              <div className="font-bold text-slate-100">₹{item.ltp}</div>
                              <div className="text-[10px] text-slate-400">VWAP: ₹{item.vwap}</div>
                            </td>

                            {/* First Radar Time */}
                            <td className="py-3.5 px-3 text-slate-300">
                              {item.first_radar_time || '-'}
                            </td>

                            {/* Zone Confirmed Time */}
                            <td className="py-3.5 px-3 text-slate-300">
                              {item.zone_confirmed_time || '-'}
                            </td>

                            {/* Zone */}
                            <td className="py-3.5 px-3">
                              {hasZone ? (
                                <div className="text-brand-400 font-semibold text-[11px]">
                                  {item.zone}
                                </div>
                              ) : (
                                <span className="text-slate-600 font-sans text-xs">Forming...</span>
                              )}
                            </td>

                            {/* Signal / Entry Time */}
                            <td className="py-3.5 px-3 bg-brand-500/5 text-brand-300 font-semibold">
                              {item.retest_time !== '-' ? item.retest_time : (
                                <span className="text-slate-600 font-sans font-normal text-xs">Waiting retest</span>
                              )}
                            </td>

                            {/* Exact Entry Price */}
                            <td className="py-3.5 px-3 bg-brand-500/10">
                              {hasEntry ? (
                                <span className="text-white font-extrabold text-sm px-2 py-0.5 rounded bg-brand-600 shadow-md">
                                  ₹{item.entry}
                                </span>
                              ) : (
                                <span className="text-slate-600 font-sans text-xs">Pending confirmation</span>
                              )}
                            </td>

                            {/* Stop Loss */}
                            <td className="py-3.5 px-3">
                              {item.stop ? (
                                <span className="text-rose-400 font-bold">₹{item.stop}</span>
                              ) : (
                                <span className="text-slate-600">-</span>
                              )}
                            </td>

                            {/* Target (2R) */}
                            <td className="py-3.5 px-3">
                              {item.target ? (
                                <span className="text-emerald-400 font-bold">₹{item.target}</span>
                              ) : (
                                <span className="text-slate-600">-</span>
                              )}
                            </td>

                            {/* Status */}
                            <td className="py-3.5 px-4">
                              <span className={`px-2.5 py-1 rounded-md text-[10px] border tracking-wider uppercase ${statusBadge}`}>
                                {item.entry ? `SIGNAL: ENTER @ ₹${item.entry}` : item.status.replace(/_/g, ' ')}
                              </span>
                            </td>

                            {/* Interactive Chart Action */}
                            <td className="py-3.5 px-4 text-right">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setChartModalStock(item);
                                }}
                                className="px-3 py-1.5 bg-cyan-500/10 hover:bg-cyan-500/25 text-cyan-300 hover:text-cyan-200 border border-cyan-500/30 rounded-xl text-xs font-bold inline-flex items-center gap-1.5 transition shadow-sm hover:scale-105 active:scale-95"
                              >
                                <BarChart3 className="w-3.5 h-3.5" />
                                <span>Chart</span>
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Quick Cards: Spotlight on Scanned Setups */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {top10Items.slice(0, 3).map((item) => (
                <div key={item.symbol} className="glass-panel p-5 rounded-2xl border border-dark-700 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-base text-white">{item.symbol}</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          item.direction === 'BULLISH' ? 'bg-bull/20 text-bull-light' : 'bg-bear/20 text-bear-light'
                        }`}>
                          {item.direction}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400">{item.name}</p>
                    </div>

                    <div className="text-right">
                      <div className="text-sm font-bold text-white font-mono">₹{item.ltp}</div>
                      <div className="text-[10px] text-slate-400 font-mono">VWAP: ₹{item.vwap}</div>
                    </div>
                  </div>

                  <div className="p-3 bg-dark-800 rounded-xl border border-dark-750 text-xs font-mono space-y-1.5">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Entry Price:</span>
                      <span className="text-white font-bold">{item.entry ? `₹${item.entry}` : 'Awaiting 3m confirmation'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Entry Time:</span>
                      <span className="text-brand-400">{item.retest_time !== '-' ? item.retest_time : 'Pending retest'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Stop Loss:</span>
                      <span className="text-rose-400">{item.stop ? `₹${item.stop}` : '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Target (2R):</span>
                      <span className="text-emerald-400">{item.target ? `₹${item.target}` : '-'}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 2: BACKTESTER (HISTORICAL SIGNALS IDENTIFIER)          */}
        {/* ========================================================= */}
        {activeTab === 'backtest' && (
          <div className="space-y-6">
            <div className="glass-panel p-6 rounded-2xl space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                      ⚡ STRICTLY INTRADAY
                    </span>
                    <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                      <BarChart2 className="h-5 w-5 text-brand-500" />
                      <span>Historical Intraday Strategy Backtester</span>
                    </h2>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Evaluates intraday sessions (09:15 - 15:30 IST) across F&O stocks. Entry window: <strong>09:45 - 14:30 IST</strong>. Compulsory square-off: <strong>15:15 IST</strong>. Zero overnight hold.
                  </p>
                </div>

                {backtestHistory.length > 0 && (
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-slate-400">Previous Runs:</span>
                    <select
                      onChange={(e) => e.target.value && handleSelectHistoryRun(e.target.value)}
                      className="bg-dark-800 border border-dark-700 rounded-xl px-3 py-1.5 text-xs text-slate-200 outline-none"
                    >
                      <option value="">Select a previous run...</option>
                      {backtestHistory.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.created_at} | {r.symbols} | Win {r.win_rate}% | PnL ₹{r.total_pnl}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              <form onSubmit={handleRunBacktest} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-4 items-end pt-2">
                <div className="lg:col-span-2">
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Stock Universe
                  </label>
                  <select
                    value={backtestSymbol}
                    onChange={(e) => setBacktestSymbol(e.target.value)}
                    className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none focus:border-brand-500"
                  >
                    <option value="ALL">✨ ALL F&O Stocks (Batch Universe)</option>
                    {availableStocks.map((s) => (
                      <option key={s.symbol} value={s.symbol}>
                        {s.symbol} - {s.name} ({s.sector})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="lg:col-span-1">
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Strategy
                  </label>
                  <select
                    value={backtestStrategy}
                    onChange={(e) => setBacktestStrategy(e.target.value)}
                    className="w-full bg-dark-800 border border-dark-700 rounded-xl px-2.5 py-2 text-xs text-slate-100 outline-none focus:border-brand-500"
                  >
                    <option value="ALL">✨ Multi (SMC+OB)</option>
                    <option value="SMC_FVG">⚡ SMC FVG</option>
                    <option value="ORDER_BLOCK">🧱 OB Retest</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">From Date</label>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    required
                    className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none focus:border-brand-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">To Date</label>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    required
                    className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none focus:border-brand-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">Capital (₹) / Risk</label>
                  <div className="flex items-center space-x-1">
                    <input
                      type="number"
                      value={initialCapital}
                      onChange={(e) => setInitialCapital(e.target.value)}
                      className="w-full bg-dark-800 border border-dark-700 rounded-xl px-2.5 py-2 text-xs text-slate-100 outline-none focus:border-brand-500 font-mono"
                    />
                    <span className="text-[11px] text-slate-400 font-mono">0.5%</span>
                  </div>
                </div>

                <div>
                  <button
                    type="submit"
                    disabled={backtestLoading}
                    className="w-full bg-brand-600 hover:bg-brand-500 text-white font-semibold text-xs py-2.5 px-4 rounded-xl transition shadow-lg shadow-brand-500/20 flex items-center justify-center space-x-2"
                  >
                    {backtestLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 fill-current" />}
                    <span>Run Backtest</span>
                  </button>
                </div>

              </form>
            </div>

            {backtestError && (
              <div className="p-3 rounded-xl border bg-bear/10 border-bear/30 text-bear-light text-xs">{backtestError}</div>
            )}

            {backtestResult && (
              <div className="space-y-6">
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                  <div className="bg-dark-850 p-4 rounded-xl border border-dark-700">
                    <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1">Total PnL</div>
                    <div className={`text-lg font-extrabold font-mono ${backtestResult.summary.total_pnl >= 0 ? 'text-bull' : 'text-bear'}`}>
                      {backtestResult.summary.total_pnl >= 0 ? '+' : ''}₹{backtestResult.summary.total_pnl?.toLocaleString()}
                    </div>
                    <div className="text-xs font-mono text-bull-light mt-0.5">
                      +{backtestResult.summary.total_pnl_pct}%
                    </div>
                  </div>

                  <div className="bg-dark-850 p-4 rounded-xl border border-dark-700">
                    <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1">Win Rate</div>
                    <div className="text-lg font-extrabold font-mono text-white">{backtestResult.summary.win_rate}%</div>
                    <div className="text-xs text-slate-400 font-mono mt-0.5">
                      {backtestResult.summary.wins}W / {backtestResult.summary.losses}L
                    </div>
                  </div>

                  <div className="bg-dark-850 p-4 rounded-xl border border-dark-700">
                    <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1">Profit Factor</div>
                    <div className="text-lg font-extrabold font-mono text-brand-400">{backtestResult.summary.profit_factor}</div>
                    <div className="text-[10px] text-slate-500">Gross W / Gross L</div>
                  </div>

                  <div className="bg-dark-850 p-4 rounded-xl border border-dark-700">
                    <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1">Max Drawdown</div>
                    <div className="text-lg font-extrabold font-mono text-rose-400">-{backtestResult.summary.max_drawdown_pct}%</div>
                    <div className="text-xs text-slate-400 font-mono mt-0.5">-₹{backtestResult.summary.max_drawdown?.toLocaleString()}</div>
                  </div>

                  <div className="bg-dark-850 p-4 rounded-xl border border-dark-700">
                    <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1">Intraday Trades</div>
                    <div className="text-lg font-extrabold font-mono text-slate-200">{backtestResult.summary.total_trades}</div>
                    <div className="text-[10px] text-slate-500">
                      {backtestResult.summary.eod_square_offs || 0} EOD 15:15 Exits
                    </div>
                  </div>

                  <div className="bg-dark-850 p-4 rounded-xl border border-dark-700">
                    <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1">Avg Trade</div>
                    <div className="text-lg font-extrabold font-mono text-slate-200">₹{backtestResult.summary.avg_trade_pnl?.toLocaleString()}</div>
                    <div className="text-[10px] text-slate-500">
                      {backtestResult.summary.avg_r != null ? `${backtestResult.summary.avg_r}R avg · ₹${backtestResult.summary.total_costs?.toLocaleString()} costs` : 'Expectancy'}
                    </div>
                  </div>
                </div>

                <div className="glass-panel rounded-2xl overflow-hidden border border-dark-700">
                  <div className="p-4 bg-dark-850 border-b border-dark-700 flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-white">Intraday Identified Setups & Execution Log</h3>
                      <p className="text-xs text-slate-400">Every trade strictly enters between 09:45–14:30 and exits by 15:15 IST.</p>
                    </div>
                    <span className="text-xs text-slate-400 font-mono">({backtestResult.trades?.length} setups)</span>
                  </div>

                  <div className="overflow-x-auto max-h-[500px]">
                    <table className="w-full text-left text-xs border-collapse font-mono">
                      <thead className="sticky top-0 bg-dark-800 border-b border-dark-700 text-slate-400 text-[11px] uppercase">
                        <tr>
                          <th className="py-2.5 px-3">Stock</th>
                          <th className="py-2.5 px-3">Strategy</th>
                          <th className="py-2.5 px-3">Direction</th>
                          <th className="py-2.5 px-3">Entry Time (IST)</th>
                          <th className="py-2.5 px-3">Zone (Low-High)</th>
                          <th className="py-2.5 px-3">Entry Price</th>
                          <th className="py-2.5 px-3">Stop Loss</th>
                          <th className="py-2.5 px-3">Target (2R)</th>
                          <th className="py-2.5 px-3">Exit Time (IST)</th>
                          <th className="py-2.5 px-3">Exit Price</th>
                          <th className="py-2.5 px-3">PnL (₹)</th>
                          <th className="py-2.5 px-3">Exit Reason</th>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3">Chart</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-dark-700/60">
                        {(backtestResult.trades || []).map((t, idx) => (
                          <tr key={idx} onClick={() => setChartTradeIdx(idx)} className="hover:bg-dark-750/70 transition cursor-pointer">
                            <td className="py-2 px-3 font-bold text-white">{t.symbol}</td>
                            <td className="py-2 px-3">
                              {t.strategy === 'SMC_FVG' ? (
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40">
                                  ⚡ SMC FVG
                                </span>
                              ) : (
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                                  🧱 OB Retest
                                </span>
                              )}
                            </td>
                            <td className="py-2 px-3">
                              <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                t.direction === 'BULLISH' ? 'bg-bull/20 text-bull-light' : 'bg-bear/20 text-bear-light'
                              }`}>
                                {t.direction === 'BULLISH' ? 'BUY' : 'SELL'}
                              </span>
                            </td>
                            <td className="py-2 px-3 text-brand-300 font-semibold">{t.entry_time?.split(' ')[1] || t.entry_time}</td>
                            <td className="py-2 px-3 text-slate-400">
                              ₹{t.zone_low} - ₹{t.zone_high}
                              {t.ce_mid && <span className="text-[10px] text-indigo-300 ml-1">({t.ce_mid})</span>}
                            </td>
                            <td className="py-2 px-3 text-white font-semibold">₹{t.entry_price}</td>
                            <td className="py-2 px-3 text-rose-400">₹{t.stop_loss}</td>
                            <td className="py-2 px-3 text-emerald-400">₹{t.target}</td>
                            <td className="py-2 px-3 text-slate-300 font-semibold">{t.exit_time?.split(' ')[1] || t.exit_time}</td>
                            <td className="py-2 px-3 font-semibold text-slate-200">₹{t.exit_price}</td>
                            <td className={`py-2 px-3 font-bold ${t.pnl >= 0 ? 'text-bull' : 'text-bear'}`}>
                              {t.pnl >= 0 ? '+' : ''}₹{t.pnl?.toLocaleString()}
                            </td>
                            <td className="py-2 px-3">
                              <span className="text-[10px] font-sans text-slate-300">
                                {t.exit_reason?.startsWith('TARGET_HIT') ? '🎯 Target Hit' : (
                                  t.exit_reason === 'STOP_LOSS_HIT' ? '🛑 Stop Loss Hit' : (
                                    t.exit_reason === 'BREAKEVEN_STOP' ? '⚖️ Breakeven Stop' : '⏱️ 15:15 EOD Square-Off'
                                  )
                                )}
                              </span>
                            </td>
                            <td className="py-2 px-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                t.status === 'WIN' ? 'bg-bull/20 text-bull-light' : 'bg-bear/20 text-bear-light'
                              }`}>
                                {t.status}
                              </span>
                            </td>
                            <td className="py-2 px-3">
                              <button
                                onClick={(e) => { e.stopPropagation(); setChartTradeIdx(idx); }}
                                className="px-2 py-1 rounded-lg text-[10px] font-sans font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 hover:bg-cyan-500/25 flex items-center gap-1"
                              >
                                <BarChart3 className="h-3 w-3" /> Chart
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 3: UPSTOX API                                         */}
        {/* ========================================================= */}
        {activeTab === 'auth' && (
          <div className="space-y-6">
            {authMessage && (
              <div className={`p-4 rounded-xl border flex items-center justify-between text-sm ${
                authMessage.type === 'success' ? 'bg-bull/10 border-bull/30 text-bull-light' : 'bg-bear/10 border-bear/30 text-bear-light'
              }`}>
                <span>{authMessage.text}</span>
                <button onClick={() => setAuthMessage(null)}>✕</button>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl space-y-5">
                <div className="flex items-center space-x-3">
                  <div className="h-8 w-8 rounded-lg bg-blue-500/10 text-brand-500 flex items-center justify-center border border-blue-500/20">
                    <Key className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-white">Upstox API Credentials</h3>
                    <p className="text-xs text-slate-400">OAuth 2.0 flow settings</p>
                  </div>
                </div>

                <form onSubmit={handleSaveCredentials} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1.5">API Key</label>
                    <input
                      type="text"
                      placeholder="e.g. 5f04a8b1-xxxx-xxxx"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      required
                      className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1.5">API Secret</label>
                    <input
                      type="password"
                      placeholder="••••••••••••••••"
                      value={apiSecret}
                      onChange={(e) => setApiSecret(e.target.value)}
                      required
                      className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 outline-none font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1.5">Redirect URI</label>
                    <input
                      type="text"
                      value={redirectUri}
                      onChange={(e) => setRedirectUri(e.target.value)}
                      required
                      className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 outline-none font-mono"
                    />
                  </div>

                  <div className="pt-2 flex items-center space-x-3">
                    <button
                      type="submit"
                      disabled={authLoading}
                      className="flex-1 bg-dark-700 hover:bg-dark-600 text-white font-medium text-xs py-2.5 px-4 rounded-xl border border-dark-600 transition"
                    >
                      Save Credentials
                    </button>

                    <a
                      href={apiKey ? `https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=${apiKey}&redirect_uri=${encodeURIComponent(redirectUri)}` : '#'}
                      target={apiKey ? '_blank' : '_self'}
                      rel="noreferrer"
                      className={`flex-1 flex items-center justify-center space-x-2 font-medium text-xs py-2.5 px-4 rounded-xl transition ${
                        apiKey ? 'bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-500/20' : 'bg-dark-800 text-slate-500 cursor-not-allowed border border-dark-700'
                      }`}
                    >
                      <span>Login with Upstox</span>
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </div>
                </form>
              </div>

              <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between space-y-5">
                <div>
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="h-8 w-8 rounded-lg bg-emerald-500/10 text-bull-light flex items-center justify-center border border-emerald-500/20">
                      <ShieldCheck className="h-4 w-4" />
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-white">Direct Token (Instant Access)</h3>
                      <p className="text-xs text-slate-400">Paste your daily Upstox Access Token</p>
                    </div>
                  </div>

                  <form onSubmit={handleManualTokenSubmit} className="space-y-4">
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1.5">Access Token</label>
                      <textarea
                        rows={4}
                        placeholder="Paste your active access token here..."
                        value={manualToken}
                        onChange={(e) => setManualToken(e.target.value)}
                        required
                        className="w-full bg-dark-800 border border-dark-700 rounded-xl p-3 text-xs text-slate-100 font-mono outline-none resize-none"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={authLoading || !manualToken.trim()}
                      className="w-full bg-bull/90 hover:bg-bull text-white font-medium text-xs py-2.5 px-4 rounded-xl transition shadow-lg shadow-bull/20 flex items-center justify-center space-x-2"
                    >
                      <ShieldCheck className="h-4 w-4" />
                      <span>Verify & Connect Token</span>
                    </button>
                  </form>
                </div>

                <div className="p-4 rounded-xl bg-dark-800/80 border border-dark-700 text-xs">
                  <div className="flex justify-between text-slate-400 mb-1">
                    <span>Status:</span>
                    <span className={authStatus.authenticated ? 'text-bull font-bold' : 'text-slate-400'}>
                      {authStatus.authenticated ? 'AUTHENTICATED' : 'DISCONNECTED'}
                    </span>
                  </div>
                  {authStatus.authenticated && (
                    <div className="text-[11px] font-mono text-slate-300">
                      User: {authStatus.user_name || authStatus.user_id} | Token: {authStatus.token_preview}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="glass-panel p-6 rounded-2xl space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center space-x-2">
                    <Radio className="h-4 w-4 text-amber-400 animate-pulse" />
                    <span>Single Tick Verifier (RELIANCE)</span>
                  </h3>
                  <p className="text-xs text-slate-400">Verifies live market feed connectivity</p>
                </div>
                <button
                  onClick={handlePullRelianceTick}
                  disabled={tickLoading || !authStatus.authenticated}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center space-x-2 transition ${
                    authStatus.authenticated
                      ? 'bg-brand-600 hover:bg-brand-500 text-white'
                      : 'bg-dark-800 text-slate-500 cursor-not-allowed border border-dark-700'
                  }`}
                >
                  {tickLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 fill-current" />}
                  <span>Pull RELIANCE Quote</span>
                </button>
              </div>

              {tickError && (
                <div className="p-3 bg-bear/10 border border-bear/30 text-bear-light rounded-xl text-xs">
                  {tickError}
                </div>
              )}

              {tickData && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
                  <div className="bg-dark-800 p-3 rounded-xl border border-dark-700">
                    <div className="text-slate-400 text-[10px]">LTP</div>
                    <div className="text-base font-bold text-white">₹{tickData.last_price}</div>
                  </div>
                  <div className="bg-dark-800 p-3 rounded-xl border border-dark-700">
                    <div className="text-slate-400 text-[10px]">High / Low</div>
                    <div className="text-emerald-400">H: ₹{tickData.ohlc?.high}</div>
                    <div className="text-rose-400">L: ₹{tickData.ohlc?.low}</div>
                  </div>
                  <div className="bg-dark-800 p-3 rounded-xl border border-dark-700">
                    <div className="text-slate-400 text-[10px]">Volume</div>
                    <div className="text-slate-200">{tickData.volume?.toLocaleString()}</div>
                  </div>
                  <div className="bg-dark-800 p-3 rounded-xl border border-dark-700">
                    <div className="text-slate-400 text-[10px]">Timestamp</div>
                    <div className="text-slate-300">
                      {tickData.timestamp ? new Date(Number(tickData.timestamp)).toLocaleTimeString() : 'Live'}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Stock Detail Modal */}
      {selectedStock && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-dark-850 border border-dark-700 rounded-2xl max-w-xl w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-dark-700 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                  <span>{selectedStock.symbol}</span>
                  <span className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${
                    selectedStock.direction === 'BULLISH' ? 'bg-bull/20 text-bull-light' : 'bg-bear/20 text-bear-light'
                  }`}>
                    {selectedStock.direction}
                  </span>
                </h3>
                <p className="text-xs text-slate-400">{selectedStock.name} • {selectedStock.sector}</p>
              </div>
              <button
                onClick={() => setSelectedStock(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-dark-700"
              >
                ✕
              </button>
            </div>

            <div className="p-4 bg-brand-500/10 border border-brand-500/30 rounded-xl space-y-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-brand-300">
                Setup Execution Signal
              </span>
              <div className="text-lg font-mono font-extrabold text-white">
                {selectedStock.entry ? (
                  <span>ENTER AT: ₹{selectedStock.entry} ({selectedStock.direction === 'BULLISH' ? 'BUY' : 'SELL'})</span>
                ) : (
                  <span>Zone active: Awaiting 3m retest trigger</span>
                )}
              </div>
              <div className="text-xs text-slate-300 font-mono">
                Signal Time: <strong>{selectedStock.retest_time !== '-' ? selectedStock.retest_time : 'Awaiting confirmation'}</strong>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 font-mono text-xs">
              <div className="bg-dark-800 p-3 rounded-xl border border-dark-750">
                <span className="text-slate-400 text-[10px]">Stop Loss</span>
                <div className="text-sm font-bold text-rose-400">
                  {selectedStock.stop ? `₹${selectedStock.stop}` : '-'}
                </div>
              </div>
              <div className="bg-dark-800 p-3 rounded-xl border border-dark-750">
                <span className="text-slate-400 text-[10px]">Target (2R)</span>
                <div className="text-sm font-bold text-emerald-400">
                  {selectedStock.target ? `₹${selectedStock.target}` : '-'}
                </div>
              </div>
              <div className="bg-dark-800 p-3 rounded-xl border border-dark-750">
                <span className="text-slate-400 text-[10px]">Order Block Range</span>
                <div className="text-sm font-bold text-brand-400">{selectedStock.zone}</div>
              </div>
              <div className="bg-dark-800 p-3 rounded-xl border border-dark-750">
                <span className="text-slate-400 text-[10px]">Session VWAP</span>
                <div className="text-sm font-bold text-white">₹{selectedStock.vwap}</div>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setSelectedStock(null)}
                className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-xl text-xs font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Backtest trade replay chart */}
      {chartTradeIdx !== null && backtestResult?.trades?.length > 0 && (
        <BacktestTradeChartModal
          trades={backtestResult.trades}
          index={chartTradeIdx}
          onIndexChange={setChartTradeIdx}
          onClose={() => setChartTradeIdx(null)}
        />
      )}

      {/* Interactive TradingView Lightweight Candlestick Chart Modal */}
      <StockChartModal
        stock={chartModalStock}
        isOpen={Boolean(chartModalStock)}
        onClose={() => setChartModalStock(null)}
      />
    </div>
  );
}
