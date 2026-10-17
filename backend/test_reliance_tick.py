#!/usr/bin/env python3
"""
Test script to pull a single live tick of 'RELIANCE' to prove Upstox API connection.
Usage:
    python test_reliance_tick.py [optional_access_token]
"""

import sys
import os
import json
from pathlib import Path

# Add backend directory to sys.path so we can import app modules
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from app.config import current_settings, load_settings
from app.core.upstox_service import upstox_service

RELIANCE_INSTRUMENT_KEY = "NSE_EQ|INE002A01018"

def test_tick(token: str = None):
    print("=" * 60)
    print(" UPSTOX API CONNECTION TEST - RELIANCE TICK ")
    print("=" * 60)
    
    settings = load_settings()
    access_token = token or settings.access_token or os.getenv("UPSTOX_ACCESS_TOKEN")
    
    if not access_token:
        print("\n❌ ERROR: No Upstox Access Token found!")
        print("\nPlease provide your Upstox Access Token using either:")
        print("  1. Pass as argument: python test_reliance_tick.py <YOUR_ACCESS_TOKEN>")
        print("  2. Set in environment: export UPSTOX_ACCESS_TOKEN='<YOUR_TOKEN>'")
        print("  3. Authenticate via the Web UI at http://localhost:5173\n")
        sys.exit(1)

    current_settings.access_token = access_token

    print(f"\n🔑 Using Token: {access_token[:8]}...{access_token[-4:] if len(access_token) > 12 else '***'}")
    
    # 1. Test Profile first
    print("\n[Step 1/2] Verifying User Profile with Upstox...")
    profile_res = upstox_service.get_profile(access_token)
    if profile_res.get("status") == "success":
        user_info = profile_res.get("data", {})
        print(f"✅ User Authenticated: {user_info.get('user_name', 'N/A')} ({user_info.get('user_id', 'N/A')})")
        print(f"   Email: {user_info.get('email', 'N/A')}")
        print(f"   Broker: {user_info.get('broker', 'Upstox')}")
    else:
        print(f"⚠️ Profile check warning: {profile_res.get('message')}")
        print("   Attempting market quote directly...")

    # 2. Pull Single Live Quote/Tick for RELIANCE
    print(f"\n[Step 2/2] Fetching live quote for RELIANCE ({RELIANCE_INSTRUMENT_KEY})...")
    quote_res = upstox_service.get_market_quote(RELIANCE_INSTRUMENT_KEY)
    
    if quote_res.get("status") == "success":
        data = quote_res.get("data", {})
        # Find the reliance key in dictionary (might be 'NSE_EQ:RELIANCE' or 'NSE_EQ|INE002A01018')
        reliance_quote = None
        for k, v in data.items():
            if "RELIANCE" in k or "INE002A01018" in k or k == RELIANCE_INSTRUMENT_KEY:
                reliance_quote = v
                break
        if not reliance_quote and len(data) > 0:
            reliance_quote = list(data.values())[0]

        print("\n" + "=" * 60)
        print("🎯 LIVE TICK RECEIVED SUCCESSFULLY")
        print("=" * 60)
        if isinstance(reliance_quote, dict):
            ohlc = reliance_quote.get("ohlc", {})
            depth = reliance_quote.get("depth", {})
            ltp = reliance_quote.get("last_price")
            volume = reliance_quote.get("volume")
            timestamp = reliance_quote.get("timestamp")
            close = ohlc.get("close")
            change = (ltp - close) if (ltp and close) else 0
            pct_change = (change / close * 100) if close else 0
            
            print(f"Instrument   : RELIANCE ({RELIANCE_INSTRUMENT_KEY})")
            print(f"Last Price   : ₹{ltp}")
            print(f"Change       : {change:+.2f} ({pct_change:+.2f}%)")
            print(f"Volume       : {volume:,}" if volume else f"Volume: {volume}")
            print(f"Day Open     : ₹{ohlc.get('open')}")
            print(f"Day High     : ₹{ohlc.get('high')}")
            print(f"Day Low      : ₹{ohlc.get('low')}")
            print(f"Prev Close   : ₹{ohlc.get('close')}")
            print(f"Timestamp    : {timestamp}")
            
            buy_depth = depth.get("buy", [])
            sell_depth = depth.get("sell", [])
            if buy_depth and sell_depth:
                best_bid = buy_depth[0].get("price") if buy_depth else "N/A"
                best_ask = sell_depth[0].get("price") if sell_depth else "N/A"
                print(f"Best Bid/Ask : ₹{best_bid} / ₹{best_ask}")
        else:
            print(json.dumps(data, indent=2))
        
        print("\n✅ Connection test PASSED! Upstox API is operational.")
        return True
    else:
        print(f"\n❌ FAILED to pull market tick: {quote_res.get('message')}")
        print("\nTroubleshooting tips:")
        print(" - Verify your Upstox access token has not expired (tokens expire daily at 03:30 AM IST).")
        print(" - Ensure your Upstox app has market data permissions enabled.")
        sys.exit(1)

if __name__ == "__main__":
    cli_token = sys.argv[1] if len(sys.argv) > 1 else None
    test_tick(cli_token)
