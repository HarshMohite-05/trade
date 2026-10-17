import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trading.db"
DB_PATH.parent.mkdir(exist_ok=True)

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Candles table (3m and 5m)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume REAL NOT NULL,
        vwap REAL DEFAULT 0,
        UNIQUE(symbol, timeframe, timestamp)
    )
    """)

    # Trades log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        entry_time TEXT NOT NULL,
        entry_price REAL NOT NULL,
        stop_loss REAL NOT NULL,
        target REAL NOT NULL,
        exit_time TEXT,
        exit_price REAL,
        pnl REAL DEFAULT 0,
        pnl_pct REAL DEFAULT 0,
        r_multiple REAL DEFAULT 0,
        status TEXT NOT NULL,
        zone_high REAL,
        zone_low REAL,
        confirmation_time TEXT,
        exit_reason TEXT,
        strategy TEXT DEFAULT 'ORDER_BLOCK'
    )
    """)

    # Backtest runs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS backtest_runs (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        symbols TEXT NOT NULL,
        date_from TEXT NOT NULL,
        date_to TEXT NOT NULL,
        initial_capital REAL NOT NULL,
        total_trades INTEGER NOT NULL,
        wins INTEGER NOT NULL,
        losses INTEGER NOT NULL,
        win_rate REAL NOT NULL,
        total_pnl REAL NOT NULL,
        total_pnl_pct REAL NOT NULL,
        profit_factor REAL NOT NULL,
        max_drawdown REAL NOT NULL,
        max_drawdown_pct REAL NOT NULL,
        strategy TEXT DEFAULT 'ORDER_BLOCK'
    )
    """)

    # Migrations for existing DB
    try:
        cursor.execute("ALTER TABLE trades ADD COLUMN strategy TEXT DEFAULT 'ORDER_BLOCK'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE backtest_runs ADD COLUMN strategy TEXT DEFAULT 'ORDER_BLOCK'")
    except Exception:
        pass
    for col, typ in (("ce_mid", "REAL"), ("shares", "INTEGER"), ("costs", "REAL"),
                     ("gross_pnl", "REAL"), ("retest_time", "TEXT")):
        try:
            cursor.execute(f"ALTER TABLE trades ADD COLUMN {col} {typ}")
        except Exception:
            pass

    conn.commit()
    conn.close()

init_db()

def save_backtest_run(run_data: Dict[str, Any], trades: List[Dict[str, Any]]) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO backtest_runs (
        id, created_at, symbols, date_from, date_to, initial_capital,
        total_trades, wins, losses, win_rate, total_pnl, total_pnl_pct,
        profit_factor, max_drawdown, max_drawdown_pct, strategy
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_data["id"], run_data["created_at"], run_data["symbols"],
        run_data["date_from"], run_data["date_to"], run_data["initial_capital"],
        run_data["total_trades"], run_data["wins"], run_data["losses"],
        run_data["win_rate"], run_data["total_pnl"], run_data["total_pnl_pct"],
        run_data["profit_factor"], run_data["max_drawdown"], run_data["max_drawdown_pct"],
        run_data.get("strategy", "ORDER_BLOCK")
    ))

    for t in trades:
        cursor.execute("""
        INSERT INTO trades (
            run_id, symbol, direction, entry_time, entry_price, stop_loss, target,
            exit_time, exit_price, pnl, pnl_pct, r_multiple, status, zone_high, zone_low,
            confirmation_time, exit_reason, strategy, ce_mid, shares, costs, gross_pnl, retest_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_data["id"], t["symbol"], t["direction"], t["entry_time"], t["entry_price"],
            t["stop_loss"], t["target"], t.get("exit_time"), t.get("exit_price"),
            t.get("pnl", 0), t.get("pnl_pct", 0), t.get("r_multiple", 0), t["status"],
            t.get("zone_high"), t.get("zone_low"), t.get("confirmation_time"), t.get("exit_reason"),
            t.get("strategy", "ORDER_BLOCK"), t.get("ce_mid"), t.get("shares"), t.get("costs"),
            t.get("gross_pnl"), t.get("retest_time")
        ))

    conn.commit()
    conn.close()

def get_backtest_runs(limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM backtest_runs ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_backtest_trades(run_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE run_id = ? ORDER BY id ASC", (run_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
