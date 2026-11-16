import asyncio
import json
from typing import Optional, Dict, Any
import websockets


class BackendWebSocketClient:
    """Asynchronous WebSocket client connecting Vision Agent to FastAPI backend."""

    def __init__(self, ws_url: str = "ws://127.0.0.1:8000/api/v1/ws/stream"):
        self.ws_url = ws_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.send_queue = asyncio.Queue()

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.ws_url)
            self.connected = True
            print(f"[WebSocketClient] Connected to backend at {self.ws_url}")
            asyncio.create_task(self._sender_loop())
        except Exception as e:
            self.connected = False
            print(f"[WebSocketClient] Warning: Could not connect to backend ({e}). Running in offline/standalone mode.")

    async def _sender_loop(self):
        while self.connected and self.websocket:
            try:
                data = await self.send_queue.get()
                await self.websocket.send(json.dumps(data))
                self.send_queue.task_done()
            except Exception as e:
                print(f"[WebSocketClient] Error sending telemetry: {e}")
                self.connected = False
                break

    def send_telemetry_sync(self, payload: Dict[str, Any]):
        """Non-blocking telemetry enqueue."""
        if self.connected:
            try:
                self.send_queue.put_nowait(payload)
            except Exception:
                pass

    async def close(self):
        self.connected = False
        if self.websocket:
            await self.websocket.close()
