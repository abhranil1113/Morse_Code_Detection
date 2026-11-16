import sys
import os
from pathlib import Path
import base64
import numpy as np
import cv2

# Add project root to sys.path so 'vision' and 'backend' are discoverable
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.core.config import settings
from app.db.schema import init_db
from app.modules.auth.router import router as auth_router
from app.modules.rooms.router import router as rooms_router
from app.modules.messages.router import router as messages_router
from app.modules.calibrations.router import router as calibrations_router
from app.websocket.manager import ws_manager

_vision_bridge = None

def get_vision_bridge():
    global _vision_bridge
    if _vision_bridge is None:
        try:
            from vision.agent.local_bridge import LocalVisionBridge
            _vision_bridge = LocalVisionBridge()
        except Exception as e:
            print(f"[Warning] Failed to initialize LocalVisionBridge: {e}")
    return _vision_bridge


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB schema safely
    try:
        await init_db()
    except Exception as e:
        print(f"Database initialization warning (ensure PostgreSQL is running): {e}")
    yield
    # Shutdown: Cleanly dispose all async engine connections while event loop is still active
    try:
        from app.db.db_connection import dispose_engine
        await dispose_engine()
    except Exception:
        pass


API_DESCRIPTION = """
## EyeSpeak AI — Real-Time Assistive Communication Platform

EyeSpeak AI translates intentional eye blinks and gaze movements into speech, Morse code, and text in real time.

### Key Capabilities:
* **Authentication**: Bcrypt password hashing, JWT access tokens, and SHA-256 hashed refresh tokens with automatic rotation.
* **Communication Sessions**: Multi-user channels with real-time participation (`SPEAKER`, `ASSISTANT`, `OBSERVER`).
* **Message Delivery**: Eye-spoken Morse messages persisted with transcript, confidence scores, and broadcasted via WebSockets.
* **Vision Calibrations**: Per-user, per-device webcam calibration profiles for personalized EAR thresholds and blink timings.
* **WebSocket Streaming**: Bi-directional channels for real-time vision telemetry and multi-user chat.

### Interactive Swagger Usage:
1. Register an account at `POST /api/v1/auth/register` or sign in at `POST /api/v1/auth/login`.
2. Copy the returned `access_token`.
3. Click the **Authorize 🔓** button at the top right of this page and paste your token in `bearerAuth` as `Bearer <token>` (or raw token).
4. All protected endpoints are now authorized for interactive testing.
"""

tags_metadata = [
    {
        "name": "Authentication",
        "description": "User registration, credential login, token rotation via refresh token, session revocation, and profile inspection.",
    },
    {
        "name": "Rooms & Communication Sessions",
        "description": "Creation, discovery, membership management, and lifecycle controls for assistive communication sessions.",
    },
    {
        "name": "Messages",
        "description": "Send and retrieve eye-spoken Morse messages with audit trails and real-time broadcasts.",
    },
    {
        "name": "Vision Calibrations",
        "description": "Manage personalized webcam Eye Aspect Ratio (EAR) thresholds, blink timings, and model parameters.",
    },
    {
        "name": "System & Health",
        "description": "Service heartbeat, health checks, and platform metadata.",
    },
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=API_DESCRIPTION,
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "defaultModelsExpandDepth": 2,
        "docExpansion": "list",
        "filter": True
    }
)

# CORS Middleware for React & Vite Frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(rooms_router, prefix=settings.API_V1_STR)
app.include_router(messages_router, prefix=settings.API_V1_STR)
app.include_router(calibrations_router, prefix=settings.API_V1_STR)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=tags_metadata,
    )

    # Add Bearer Token security scheme for Swagger UI
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": f"{settings.API_V1_STR}/auth/login",
                    "scopes": {}
                }
            }
        },
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT Bearer token in the format: `Bearer <token>` or raw `<token>`"
        }
    }

    # Apply bearerAuth globally or per endpoint
    openapi_schema["security"] = [{"bearerAuth": []}, {"OAuth2PasswordBearer": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/", tags=["System & Health"], summary="Root API Information")
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": f"{settings.API_V1_STR}/openapi.json"
    }


@app.get("/health", tags=["System & Health"], summary="Service Health Check")
async def health():
    return {"status": "healthy"}


# WebSocket Endpoint for Vision Agent & Frontend Telemetry
@app.websocket("/api/v1/ws/stream")
@app.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    """
    Bi-directional stream:
    - Vision Agent publishes EAR, Eye State, Morse Dots/Dashes, Decoded Words.
    - Frontend can stream video frames for real-time browser eye tracking.
    - Frontend subscribes and updates live visual indicators.
    """
    await ws_manager.connect_stream(websocket)
    bridge = get_vision_bridge()
    try:
        while True:
            data = await websocket.receive_json()
            if isinstance(data, dict) and data.get("type") == "frame" and "image" in data and bridge is not None:
                try:
                    img_data = data["image"]
                    if "," in img_data:
                        img_data = img_data.split(",", 1)[1]
                    img_bytes = base64.b64decode(img_data)
                    np_arr = np.frombuffer(img_bytes, np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        telemetry = bridge.process_frame(frame)
                        telemetry.pop("processed_frame", None)
                        await ws_manager.broadcast_stream(telemetry)
                except Exception:
                    pass
            else:
                # Direct telemetry broadcast from standalone Python agent or tests
                await ws_manager.broadcast_stream(data)
    except WebSocketDisconnect:
        ws_manager.disconnect_stream(websocket)
    except Exception:
        ws_manager.disconnect_stream(websocket)
    except Exception:
        ws_manager.disconnect_stream(websocket)


# WebSocket Endpoint for Live Room Chat & Communication Sessions
@app.websocket("/api/v1/ws/rooms/{room_id}")
@app.websocket("/ws/communication-sessions/{room_id}")
async def websocket_room_endpoint(websocket: WebSocket, room_id: str):
    await ws_manager.connect_room(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.broadcast_to_room(room_id, data)
    except WebSocketDisconnect:
        ws_manager.disconnect_room(room_id, websocket)
    except Exception:
        ws_manager.disconnect_room(room_id, websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
