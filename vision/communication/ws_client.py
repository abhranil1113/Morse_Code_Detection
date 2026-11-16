import asyncio
import json
import logging
from typing import Optional, Dict, Any, Callable
import websockets

logger = logging.getLogger("vision.communication.ws_client")


class VisionWebSocketClient:
    """
    Resilient WebSocket client connecting the local vision agent to FastAPI backend.
    Features:
    - Auto-reconnect with exponential backoff
    - Queue-based non-blocking transmission
    - JWT authentication token support
    - Graceful shutdown
    """

    def __init__(
        self,
        ws_url: str = "ws://127.0.0.1:8000/api/v1/ws/stream",
        auth_token: Optional[str] = None,
        max_reconnect_delay: float = 30.0
    ):
        self.base_url = ws_url
        self.auth_token = auth_token
        self.max_reconnect_delay = max_reconnect_delay
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running = False
        self.is_connected = False
        self.send_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.on_message_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self._worker_task: Optional[asyncio.Task] = None

    @property
    def target_url(self) -> str:
        if self.auth_token:
            delim = "&" if "?" in self.base_url else "?"
            return f"{self.base_url}{delim}token={self.auth_token}"
        return self.base_url

    async def start(self):
        self.is_running = True
        self._worker_task = asyncio.create_task(self._connection_loop())

    async def _connection_loop(self):
        delay = 1.0
        while self.is_running:
            try:
                logger.info(f"Connecting to backend WebSocket at {self.base_url}...")
                headers = {}
                if self.auth_token:
                    headers["Authorization"] = f"Bearer {self.auth_token}"

                async with websockets.connect(self.target_url, extra_headers=headers) as ws:
                    self.websocket = ws
                    self.is_connected = True
                    delay = 1.0
                    logger.info("Connected to EyeSpeak backend stream successfully.")

                    send_task = asyncio.create_task(self._send_loop(ws))
                    recv_task = asyncio.create_task(self._recv_loop(ws))

                    done, pending = await asyncio.wait(
                        [send_task, recv_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in pending:
                        task.cancel()

            except Exception as e:
                self.is_connected = False
                self.websocket = None
                if self.is_running:
                    logger.warning(f"WebSocket disconnected ({e}). Reconnecting in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    delay = min(delay * 1.5, self.max_reconnect_delay)

    async def _send_loop(self, ws: websockets.WebSocketClientProtocol):
        while self.is_running and self.is_connected:
            try:
                data = await self.send_queue.get()
                payload = json.dumps(data)
                await ws.send(payload)
                self.send_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error sending telemetry packet: {e}")
                break

    async def _recv_loop(self, ws: websockets.WebSocketClientProtocol):
        while self.is_running and self.is_connected:
            try:
                message = await ws.recv()
                if self.on_message_callback:
                    parsed = json.loads(message)
                    self.on_message_callback(parsed)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Receive loop terminating: {e}")
                break

    def send_event_sync(self, payload: Dict[str, Any]):
        """Thread-safe, non-blocking enqueue of vision telemetry or blink event."""
        if not self.is_connected:
            return
        try:
            self.send_queue.put_nowait(payload)
        except asyncio.QueueFull:
            # Drop older frames to prevent queue backlog
            try:
                _ = self.send_queue.get_nowait()
                self.send_queue.put_nowait(payload)
            except Exception:
                pass

    async def stop(self):
        self.is_running = False
        self.is_connected = False
        if self._worker_task:
            self._worker_task.cancel()
        if self.websocket:
            await self.websocket.close()
