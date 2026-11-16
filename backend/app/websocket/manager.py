import json
from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # Maps room_id -> list of active WebSockets
        self.active_rooms: Dict[str, List[WebSocket]] = {}
        # Global telemetry stream sockets (from OpenCV vision agent to frontend)
        self.stream_subscribers: List[WebSocket] = []

    async def connect_room(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_rooms:
            self.active_rooms[room_id] = []
        self.active_rooms[room_id].append(websocket)

    def disconnect_room(self, room_id: str, websocket: WebSocket):
        if room_id in self.active_rooms:
            if websocket in self.active_rooms[room_id]:
                self.active_rooms[room_id].remove(websocket)
            if not self.active_rooms[room_id]:
                del self.active_rooms[room_id]

    async def broadcast_to_room(self, room_id: str, message: dict):
        if room_id in self.active_rooms:
            payload = json.dumps(message)
            for connection in self.active_rooms[room_id]:
                try:
                    await connection.send_text(payload)
                except Exception:
                    pass

    async def connect_stream(self, websocket: WebSocket):
        await websocket.accept()
        self.stream_subscribers.append(websocket)

    def disconnect_stream(self, websocket: WebSocket):
        if websocket in self.stream_subscribers:
            self.stream_subscribers.remove(websocket)

    async def broadcast_stream(self, data: dict):
        payload = json.dumps(data)
        for connection in self.stream_subscribers:
            try:
                await connection.send_text(payload)
            except Exception:
                pass


ws_manager = ConnectionManager()
