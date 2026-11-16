# EyeSpeak AI — Complete API & Swagger Documentation

**EyeSpeak AI** is a real-time assistive communication platform that translates intentional eye blinks and gaze movements into speech, Morse code, and text.

This document provides a comprehensive technical reference for all REST endpoints, WebSocket channels, authentication workflows, request/response models, and Swagger UI interactive testing.

---

## 1. Interactive Swagger & OpenAPI UIs

When the FastAPI server is running on `http://127.0.0.1:8000`, the interactive API explorers are available at:

- **Swagger UI (Interactive Playground)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc (Detailed Specifications)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Raw OpenAPI 3.1 JSON Schema**: [http://127.0.0.1:8000/api/v1/openapi.json](http://127.0.0.1:8000/api/v1/openapi.json)

### How to Authenticate in Swagger UI:
1. Scroll to the **Authentication** section in Swagger UI.
2. Execute `POST /api/v1/auth/register` (or `POST /api/v1/auth/login`) with valid credentials.
3. Copy the returned `access_token` string.
4. Click the green **Authorize 🔓** button at the top right of the Swagger UI page.
5. In the `bearerAuth` field, enter your token (e.g. `Bearer <your_token>` or simply the raw `<your_token>`).
6. Click **Authorize** $\rightarrow$ **Close**.
7. All protected endpoints now automatically transmit your Bearer JWT token with interactive requests.

---

## 2. Authentication & Security Architecture

- **Password Hashing**: Bcrypt with auto-salted rounds (`rounds=12`).
- **Access Tokens**: Short-lived JSON Web Tokens (JWT) signed using HMAC-SHA256 (`HS256`).
- **Refresh Tokens**: Long-lived tokens stored as cryptographic SHA-256 hashes in the `auth_sessions` table.
- **Token Rotation**: Every `/auth/refresh` invocation revokes the existing refresh session and issues a new access/refresh token pair.
- **Session Revocation**: `/auth/logout` flags the refresh session as `revoked_at = NOW()`, immediately preventing token regeneration.

---

## 3. REST API Endpoint Reference

All v1 routes are prefixed with `/api/v1`.

### A. System & Health

#### `GET /`
- **Summary**: Platform root metadata.
- **Authentication**: None.
- **Response** (`200 OK`):
  ```json
  {
    "project": "EyeSpeak AI",
    "version": "1.0.0",
    "status": "online",
    "docs_url": "/docs",
    "redoc_url": "/redoc",
    "openapi_url": "/api/v1/openapi.json"
  }
  ```

#### `GET /health`
- **Summary**: Health check probe for load balancers and container orchestrators.
- **Authentication**: None.
- **Response** (`200 OK`):
  ```json
  {
    "status": "healthy"
  }
  ```

---

### B. Authentication (`/api/v1/auth`)

#### 1. `POST /api/v1/auth/register`
- **Summary**: Register a new user account.
- **Request Body** (`application/json`):
  ```json
  {
    "email": "speaker@eyespeak.ai",
    "username": "AlexSpeaker",
    "password": "SecurePassword123!",
    "role": "USER"
  }
  ```
- **Responses**:
  - `201 Created`:
    ```json
    {
      "id": "f377e5f0-6603-42dd-b1bd-9e0341a65ddc",
      "email": "speaker@eyespeak.ai",
      "username": "AlexSpeaker",
      "display_name": "AlexSpeaker",
      "role": "USER",
      "is_active": true,
      "created_at": "2026-11-16T08:42:43.000Z"
    }
    ```
  - `400 Bad Request`: When email or display name already exists.

#### 2. `POST /api/v1/auth/login`
- **Summary**: Authenticate with email/username and password.
- **Request Body** (`application/json`):
  ```json
  {
    "email": "speaker@eyespeak.ai",
    "password": "SecurePassword123!"
  }
  ```
- **Responses**:
  - `200 OK`:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer",
      "user_id": "f377e5f0-6603-42dd-b1bd-9e0341a65ddc"
    }
    ```
  - `401 Unauthorized`: Invalid credentials.

#### 3. `POST /api/v1/auth/refresh`
- **Summary**: Rotate refresh tokens and receive new access token.
- **Request Body** (`application/json`):
  ```json
  {
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Responses**:
  - `200 OK`: Returns newly rotated `Token` object.
  - `401 Unauthorized`: Expired or revoked refresh token.

#### 4. `POST /api/v1/auth/logout`
- **Summary**: Revoke active session.
- **Request Body** (`application/json`):
  ```json
  {
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "detail": "Logged out successfully"
  }
  ```

#### 5. `GET /api/v1/auth/me`
- **Summary**: Retrieve profile of current authenticated user.
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** (`200 OK`):
  ```json
  {
    "id": "f377e5f0-6603-42dd-b1bd-9e0341a65ddc",
    "email": "speaker@eyespeak.ai",
    "username": "AlexSpeaker",
    "display_name": "AlexSpeaker",
    "role": "USER",
    "is_active": true,
    "created_at": "2026-11-16T08:42:43.000Z"
  }
  ```

---

### C. Rooms & Communication Sessions (`/api/v1/rooms`)

#### 1. `POST /api/v1/rooms`
- **Summary**: Create a new multi-user communication room.
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body** (`application/json`):
  ```json
  {
    "name": "General Assistive Room",
    "description": "Daily communication space for eye-spoken Morse.",
    "settings": {
      "auto_commit": true,
      "speech_synthesis": true
    }
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "id": "a23f7d8f-80fb-422c-9fba-5158f220aabb",
    "name": "General Assistive Room",
    "description": "Daily communication space for eye-spoken Morse.",
    "status": "ACTIVE",
    "created_by": "f377e5f0-6603-42dd-b1bd-9e0341a65ddc",
    "created_at": "2026-11-16T08:42:43.500Z"
  }
  ```

#### 2. `GET /api/v1/rooms`
- **Summary**: List active communication rooms.
- **Query Parameters**:
  - `skip` (`integer`, default: 0)
  - `limit` (`integer`, default: 100)
- **Response** (`200 OK`): Array of `RoomResponse` objects.

#### 3. `GET /api/v1/rooms/{room_id}`
- **Summary**: Retrieve specific room details.
- **Response** (`200 OK`): `RoomResponse` object.

#### 4. `POST /api/v1/rooms/{room_id}/join`
- **Summary**: Join communication room with a specified role.
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body** (`application/json`):
  ```json
  {
    "role": "SPEAKER"
  }
  ```
  *(Roles: `SPEAKER`, `ASSISTANT`, `OBSERVER`)*
- **Response** (`200 OK`):
  ```json
  {
    "id": "e9871234-abcd-ef01-2345-6789abcdef01",
    "room_id": "a23f7d8f-80fb-422c-9fba-5158f220aabb",
    "user_id": "f377e5f0-6603-42dd-b1bd-9e0341a65ddc",
    "role": "SPEAKER",
    "status": "JOINED",
    "joined_at": "2026-11-16T08:42:44.000Z"
  }
  ```

#### 5. `POST /api/v1/rooms/{room_id}/leave`
- **Summary**: Leave communication session.
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** (`200 OK`):
  ```json
  {
    "detail": "Left room successfully"
  }
  ```

#### 6. `GET /api/v1/rooms/{room_id}/members`
- **Summary**: List all participants currently or previously in the room.
- **Response** (`200 OK`): Array of `RoomMemberResponse` objects.

#### 7. `POST /api/v1/rooms/{room_id}/end`
- **Summary**: Conclude and archive communication session.
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** (`200 OK`):
  ```json
  {
    "detail": "Room ended successfully",
    "status": "COMPLETED"
  }
  ```

---

### D. Messages (`/api/v1/messages`)

#### 1. `POST /api/v1/messages`
- **Summary**: Persist eye-spoken Morse message and broadcast in real-time.
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body** (`application/json`):
  ```json
  {
    "room_id": "a23f7d8f-80fb-422c-9fba-5158f220aabb",
    "content": "HELLO WORLD",
    "input_method": "EYE_BLINK",
    "morse_raw": ".... . .-.. .-.. --- / .-- --- .-. .-.. -..",
    "confidence_score": 0.985
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "id": "acbd1ee0-3cee-4e1c-8124-a4ef7c0c0e4d",
    "room_id": "a23f7d8f-80fb-422c-9fba-5158f220aabb",
    "user_id": "f377e5f0-6603-42dd-b1bd-9e0341a65ddc",
    "content": "HELLO WORLD",
    "input_method": "EYE_BLINK",
    "morse_raw": ".... . .-.. .-.. --- / .-- --- .-. .-.. -..",
    "confidence_score": "0.9850",
    "created_at": "2026-11-16T08:42:44.200Z"
  }
  ```

#### 2. `GET /api/v1/messages/room/{room_id}`
- **Summary**: Retrieve chronological message history for a communication room.
- **Query Parameters**:
  - `limit` (`integer`, default: 50, min: 1, max: 200)
- **Response** (`200 OK`): Array of `MessageResponse` objects.

---

### E. Vision Calibrations (`/api/v1/calibrations`)

#### 1. `POST /api/v1/calibrations`
- **Summary**: Store or update personalized webcam calibration parameters.
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body** (`application/json`):
  ```json
  {
    "device_key": "webcam_logitech_c920",
    "calibration_data": {
      "ear_threshold": 0.22,
      "ear_open_mean": 0.31,
      "ear_closed_mean": 0.16,
      "dot_max_sec": 0.35,
      "dash_min_sec": 0.40
    },
    "model_version": "1.0.0-rf"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "id": "3b2c1a09-5432-6789-abcd-ef0123456789",
    "user_id": "f377e5f0-6603-42dd-b1bd-9e0341a65ddc",
    "device_key": "webcam_logitech_c920",
    "calibration_data": {
      "ear_threshold": 0.22,
      "ear_open_mean": 0.31,
      "ear_closed_mean": 0.16,
      "dot_max_sec": 0.35,
      "dash_min_sec": 0.40
    },
    "model_version": "1.0.0-rf",
    "calibrated_at": "2026-11-16T08:42:44.800Z"
  }
  ```

#### 2. `GET /api/v1/calibrations`
- **Summary**: Retrieve personalized calibration profile for a device.
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Parameters**:
  - `device_key` (`string`, required)
- **Response** (`200 OK`): `CalibrationResponse` object.

---

## 4. Real-Time WebSocket Channels

### A. Live Vision Telemetry (`/api/v1/ws/stream`)
- **URL**: `ws://127.0.0.1:8000/api/v1/ws/stream`
- **Purpose**: Connects the local OpenCV computer vision agent with frontend listeners.
- **Telemetry Packet (Client $\rightarrow$ Server $\rightarrow$ Subscribers)**:
  ```json
  {
    "face_detected": true,
    "ear": 0.28,
    "eye_state": "OPEN",
    "confidence": 0.98,
    "current_buffer": "...",
    "decoded_text": "S",
    "gaze_direction": "CENTER",
    "gesture_action": null,
    "timestamp": 1731746560.123
  }
  ```

### B. Room Live Chat & Signals (`/api/v1/ws/rooms/{room_id}`)
- **URL**: `ws://127.0.0.1:8000/api/v1/ws/rooms/{room_id}`
- **Purpose**: Broadcasts new messages, typing indications, and participant presence.
- **Broadcast Message Packet**:
  ```json
  {
    "type": "NEW_MESSAGE",
    "data": {
      "id": "acbd1ee0-3cee-4e1c-8124-a4ef7c0c0e4d",
      "room_id": "a23f7d8f-80fb-422c-9fba-5158f220aabb",
      "user_id": "f377e5f0-6603-42dd-b1bd-9e0341a65ddc",
      "content": "HELLO WORLD",
      "input_method": "EYE_BLINK",
      "morse_raw": ".... . .-.. .-.. --- / .-- --- .-. .-.. -..",
      "confidence_score": "0.9850",
      "created_at": "2026-11-16T08:42:44.200Z"
    }
  }
  ```

---

## 5. Client Integration Code Examples

### A. JavaScript / TypeScript (Fetch API)
```typescript
// 1. Authenticate
const loginRes = await fetch("http://127.0.0.1:8000/api/v1/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "speaker@eyespeak.ai", password: "SecurePassword123!" }),
});
const { access_token } = await loginRes.json();

// 2. Send Eye-Spoken Message
const msgRes = await fetch("http://127.0.0.1:8000/api/v1/messages", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${access_token}`
  },
  body: JSON.stringify({
    room_id: "a23f7d8f-80fb-422c-9fba-5158f220aabb",
    content: "YES",
    input_method: "EYE_BLINK",
    morse_raw: "-.--",
    confidence_score: 0.99
  }),
});
const message = await msgRes.json();
console.log("Message broadcasted:", message.content);
```

### B. Python (`httpx` / `requests`)
```python
import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000/api/v1")

# Authenticate
res = client.post("/auth/login", json={"email": "speaker@eyespeak.ai", "password": "SecurePassword123!"})
tokens = res.json()
headers = {"Authorization": f"Bearer {tokens['access_token']}"}

# Create Room
room = client.post("/rooms", headers=headers, json={"name": "Morning Standup"}).json()
print("Room Created:", room["id"])
```

### C. cURL
```bash
# 1. Login
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email":"speaker@eyespeak.ai","password":"SecurePassword123!"}'

# 2. List Rooms with Bearer Token
curl -X GET "http://127.0.0.1:8000/api/v1/rooms" \
     -H "Authorization: Bearer <access_token>"
```
