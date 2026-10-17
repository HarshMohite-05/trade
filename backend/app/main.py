from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.auth import router as auth_router
from .api.market import router as market_router
from .api.scanner import router as scanner_router
from .api.backtest import router as backtest_router

app = FastAPI(
    title="Order Block Trading System API",
    description="Upstox Algorithmic Trading Platform - Order Block First Retest Strategy",
    version="1.0.0"
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(market_router)
app.include_router(scanner_router)
app.include_router(backtest_router)

@app.get("/")
def root():
    return {
        "status": "online",
        "app": "Order Block First Retest Trading System",
        "version": "1.0.0",
        "endpoints": {
            "auth_status": "/api/auth/status",
            "market_tick": "/api/market/tick?instrument_key=NSE_EQ|INE002A01018",
            "scanner_state": "/api/scanner/state",
            "scanner_ws": "/ws/scanner",
            "backtest_run": "/api/backtest/run",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health():
    return {"status": "ok"}
