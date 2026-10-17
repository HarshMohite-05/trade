from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import asyncio
from ..core.scanner_engine import scanner_manager

router = APIRouter(prefix="/api/scanner", tags=["Scanner"])

@router.get("/universe")
def get_universe_list():
    """Returns the complete list of all stocks in the NSE F&O universe."""
    state = scanner_manager.get_scanner_state("ALL")
    return {
        "total": len(state["items"]),
        "stocks": state["items"]
    }

@router.get("/state")
async def get_scanner_state(
    filter: str = Query("TOP_10", description="Filter mode: TOP_10, TOP_10_BULLISH, TOP_10_BEARISH"),
    strategy: str = Query("ALL", description="Strategy: ALL, ORDER_BLOCK, SMC_FVG")
):
    """Returns the current snapshot of top 10 scanned stocks with strategy parameters and statuses."""
    return scanner_manager.get_scanner_state(filter, strategy)

@router.post("/scan-now")
async def trigger_scan(
    filter: str = Query("TOP_10"),
    strategy: str = Query("ALL", description="Strategy: ALL, ORDER_BLOCK, SMC_FVG")
):
    """Forces an immediate evaluation across all stocks in universe and returns Top 10 scanned candidates."""
    scanner_manager.sync_with_upstox_quotes()
    scanner_manager.evaluate_rankings_and_market_breadth()
    for item in scanner_manager.items.values():
        scanner_manager.check_strategy_for_item(item)
    return {
        "status": "success",
        "message": "Live Upstox API scan completed across universe. Top 10 identified stocks returned.",
        "state": scanner_manager.get_scanner_state(filter, strategy)
    }

@router.post("/simulation/start")
async def start_simulation():
    """Starts realistic live tick/candle generation and strategy evaluation."""
    scanner_manager.start_simulation()
    return {"status": "success", "message": "Simulation started", "is_simulating": True}

@router.post("/simulation/stop")
async def stop_simulation():
    """Stops the live tick simulation."""
    scanner_manager.stop_simulation()
    return {"status": "success", "message": "Simulation stopped", "is_simulating": False}

@router.websocket("/ws")
async def websocket_scanner_endpoint(websocket: WebSocket):
    """
    WebSocket connection pushing real-time table updates to the React frontend.
    """
    await websocket.accept()
    queue = asyncio.Queue()
    scanner_manager.register_client(queue)

    # Immediately push current initial state
    init_state = scanner_manager.get_scanner_state("TOP_10")
    await websocket.send_json({"type": "INITIAL_STATE", "data": init_state})

    try:
        while True:
            # Wait for either broadcast event from queue or message from client
            broadcast_task = asyncio.create_task(queue.get())
            receive_task = asyncio.create_task(websocket.receive_text())
            
            done, pending = await asyncio.wait(
                [broadcast_task, receive_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in pending:
                task.cancel()

            if broadcast_task in done:
                msg = broadcast_task.result()
                await websocket.send_json(msg)

            if receive_task in done:
                client_msg = receive_task.result()
                # If client requests instant refresh
                if client_msg == "REFRESH":
                    current_st = scanner_manager.get_scanner_state("ALL")
                    await websocket.send_json({"type": "SCANNER_UPDATE", "data": current_st})

    except WebSocketDisconnect:
        scanner_manager.unregister_client(queue)
    except Exception:
        scanner_manager.unregister_client(queue)
