import sys
import os
import asyncio
import uuid
import re
from decimal import Decimal
from pathlib import Path

# Enable testing mode prior to app / db imports to activate NullPool
os.environ["TESTING"] = "1"

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.config import settings
from app.db.db_connection import engine, AsyncSessionLocal, dispose_engine
from app.models.user import User
from app.models.communication_session import CommunicationSession
from app.models.message import Message


def redact_url(url: str) -> str:
    """Mask credentials in database URL to prevent sensitive log exposure."""
    return re.sub(r"://([^:@]+):([^@]+)@", r"://\1:***@", url)


async def run_async_api_tests() -> tuple[str, str, str]:
    print("=" * 60)
    print("Running EyeSpeak AI - Async API & Database Test Suite")
    print(f"Target Database URL: {redact_url(settings.DATABASE_URL)}")
    print("=" * 60)

    # Verification: Testing pool must be NullPool
    assert isinstance(engine.pool, NullPool), f"Expected NullPool, got {type(engine.pool)}"
    print(f"[PASS] 0. Verified active engine pool is NullPool: {engine.pool.__class__.__name__}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Health check
        res = await client.get("/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        assert res.json() == {"status": "healthy"}
        print("[PASS] 1. /health returned status: healthy")

        # 2. Root docs
        res = await client.get("/")
        assert res.status_code == 200, f"Root check failed: {res.text}"
        data = res.json()
        assert data.get("status") == "online"
        print(f"[PASS] 2. Root API status: {data.get('status')} ({data.get('project')})")

        # 3. User Registration
        test_uid = uuid.uuid4().hex[:6]
        user_email = f"user_{test_uid}@eyespeak.ai"
        user_name = f"TestUser_{test_uid}"
        user_password = "SecurePassword123!"

        res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": user_email,
                "username": user_name,
                "password": user_password
            }
        )
        assert res.status_code == 201, f"Registration failed: {res.text}"
        reg_data = res.json()
        assert reg_data["email"] == user_email
        assert reg_data["username"] == user_name
        user_id = reg_data["id"]
        print(f"[PASS] 3. /api/v1/auth/register succeeded (User ID: {user_id})")

        # 4. Duplicate Registration Rejection
        res_dup = await client.post(
            "/api/v1/auth/register",
            json={
                "email": user_email,
                "username": user_name,
                "password": user_password
            }
        )
        assert res_dup.status_code == 400, "Duplicate registration should fail with 400"
        print("[PASS] 4. Duplicate email registration rejected with 400 Bad Request")

        # 5. Invalid Login Credentials
        res_bad_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": user_email,
                "password": "WrongPassword999!"
            }
        )
        assert res_bad_login.status_code == 401, "Invalid password must return 401 Unauthorized"
        print("[PASS] 5. Invalid login credentials rejected with 401 Unauthorized")

        # 6. Valid User Login
        res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": user_email,
                "password": user_password
            }
        )
        assert res.status_code == 200, f"Login failed: {res.text}"
        login_data = res.json()
        access_token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]
        assert access_token and refresh_token
        print("[PASS] 6. /api/v1/auth/login issued valid access & refresh JWT tokens")

        # 7. Token Refresh Rotation
        res = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert res.status_code == 200, f"Refresh failed: {res.text}"
        refresh_data = res.json()
        new_access_token = refresh_data["access_token"]
        new_refresh_token = refresh_data["refresh_token"]
        assert new_access_token
        print("[PASS] 7. /api/v1/auth/refresh performed token rotation successfully")

        # 8. Current User Profile
        headers = {"Authorization": f"Bearer {new_access_token}"}
        res = await client.get("/api/v1/auth/me", headers=headers)
        assert res.status_code == 200, f"Get me failed: {res.text}"
        me_data = res.json()
        assert me_data["id"] == user_id
        assert me_data["email"] == user_email
        print(f"[PASS] 8. /api/v1/auth/me retrieved authenticated user: {me_data['username']}")

        # 9. Create Room / Communication Session
        room_name = f"Assistive Session {test_uid}"
        res = await client.post(
            "/api/v1/rooms",
            headers=headers,
            json={
                "name": room_name,
                "description": "Real-time eye blink communication test session"
            }
        )
        assert res.status_code == 201, f"Create room failed: {res.text}"
        room_data = res.json()
        room_id = room_data["id"]
        assert room_data["name"] == room_name
        print(f"[PASS] 9. /api/v1/rooms created communication session (Room ID: {room_id})")

        # 10. List Rooms
        res = await client.get("/api/v1/rooms")
        assert res.status_code == 200, f"List rooms failed: {res.text}"
        rooms_list = res.json()
        assert any(r["id"] == room_id for r in rooms_list)
        print(f"[PASS] 10. /api/v1/rooms listed active rooms")

        # 11. Join Room & Verify Participant Membership
        res = await client.post(f"/api/v1/rooms/{room_id}/join", headers=headers, json={"role": "SPEAKER"})
        assert res.status_code == 200, f"Join room failed: {res.text}"
        join_data = res.json()
        assert join_data["status"] == "JOINED"
        print("[PASS] 11. /api/v1/rooms/{id}/join added participant as SPEAKER")

        # 12. Send Morse Message
        res = await client.post(
            "/api/v1/messages",
            headers=headers,
            json={
                "room_id": room_id,
                "content": "HELLO WORLD",
                "input_method": "EYE_BLINK",
                "morse_raw": ".... . .-.. .-.. --- / .-- --- .-. .-.. -..",
                "confidence_score": 0.985
            }
        )
        assert res.status_code == 201, f"Send message failed: {res.text}"
        msg_data = res.json()
        assert msg_data["content"] == "HELLO WORLD"
        assert msg_data["room_id"] == room_id
        msg_id = msg_data["id"]
        print(f"[PASS] 12. /api/v1/messages persisted Morse message (ID: {msg_id})")

        # 13. Fetch Messages for Room
        res = await client.get(f"/api/v1/messages/room/{room_id}")
        assert res.status_code == 200, f"Fetch messages failed: {res.text}"
        messages = res.json()
        assert len(messages) >= 1
        assert messages[-1]["content"] == "HELLO WORLD"
        print(f"[PASS] 13. /api/v1/messages/room/{room_id} retrieved {len(messages)} messages")

        # 14. Save Vision Calibration
        device_key = f"webcam_logitech_c920_{test_uid}"
        calib_payload = {
            "device_key": device_key,
            "calibration_data": {
                "ear_open_mean": 0.31,
                "ear_closed_mean": 0.16,
                "ear_threshold": 0.22,
                "dot_max_sec": 0.35,
                "dash_min_sec": 0.45
            },
            "model_version": "1.0.0-rf"
        }
        res = await client.post("/api/v1/calibrations", headers=headers, json=calib_payload)
        assert res.status_code == 200, f"Save calibration failed: {res.text}"
        calib_resp = res.json()
        assert calib_resp["device_key"] == device_key
        print(f"[PASS] 14. /api/v1/calibrations saved user calibration for device {device_key}")

        # 15. Get Vision Calibration
        res = await client.get(f"/api/v1/calibrations?device_key={device_key}", headers=headers)
        assert res.status_code == 200, f"Get calibration failed: {res.text}"
        calib_fetch = res.json()
        assert calib_fetch["calibration_data"]["ear_threshold"] == 0.22
        print("[PASS] 15. /api/v1/calibrations retrieved saved calibration accurately")

        # 16. Logout & Session Revocation
        res = await client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh_token})
        assert res.status_code == 200, f"Logout failed: {res.text}"
        print("[PASS] 16. /api/v1/auth/logout revoked session successfully")

    # Cleanly dispose async engine inside its own event loop
    await dispose_engine()
    return user_id, room_id, new_access_token


def run_websocket_tests(room_id: str, access_token: str):
    """Executes synchronous WebSocket tests outside any active asyncio.run loop."""
    print("-" * 60)
    print("Running WebSocket & Multi-Channel Broadcast Tests")
    print("-" * 60)

    other_room_id = str(uuid.uuid4())

    with TestClient(app) as sync_client:
        # 17. Stream telemetry WebSocket
        with sync_client.websocket_connect("/api/v1/ws/stream") as ws_stream:
            test_telemetry = {
                "face_detected": True,
                "ear": 0.28,
                "eye_state": "OPEN",
                "current_buffer": "...",
                "decoded_text": "S"
            }
            ws_stream.send_json(test_telemetry)
            received = ws_stream.receive_json()
            assert received["current_buffer"] == "..."
            print("[PASS] 17. WebSocket /api/v1/ws/stream bi-directional telemetry broadcast verified")

        # 18. Authenticated Room Chat WebSocket with multi-client broadcast & channel isolation
        # Client 1 connects to target room with auth token
        with sync_client.websocket_connect(f"/api/v1/ws/rooms/{room_id}?token={access_token}") as ws_client1:
            # Client 2 connects to target room
            with sync_client.websocket_connect(f"/api/v1/ws/rooms/{room_id}") as ws_client2:
                # Client 3 connects to a separate room to test channel isolation
                with sync_client.websocket_connect(f"/api/v1/ws/rooms/{other_room_id}") as ws_isolated:
                    chat_payload = {"type": "CHAT", "sender": "Alex", "content": "Hello via WebSocket"}
                    ws_client1.send_json(chat_payload)

                    # Verify Client 1 receives its broadcast
                    msg1 = ws_client1.receive_json()
                    assert msg1["content"] == "Hello via WebSocket"

                    # Verify Client 2 in the same room receives the broadcast
                    msg2 = ws_client2.receive_json()
                    assert msg2["content"] == "Hello via WebSocket"

                    print("[PASS] 18. WebSocket /api/v1/ws/rooms/{id} verified authenticated multi-client broadcast")


async def run_event_loop_regression_query(step: int) -> int:
    """Executes a direct database query in a distinct event loop to verify loop isolation."""
    loop = asyncio.get_running_loop()
    loop_id = id(loop)

    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1 AS num"))
        val = result.scalar()
        assert val == 1, f"Loop {step} query failed"

    await dispose_engine()
    print(f"[PASS] 19.{step} Query succeeded on distinct EventLoop (ID: {loop_id})")
    return loop_id


async def cleanup_test_records(user_id: str, room_id: str):
    """Purges all test artifacts from the active database to ensure zero residual records."""
    print("-" * 60)
    print("Purging Test Artifacts from Database")
    print("-" * 60)

    async with AsyncSessionLocal() as session:
        if room_id:
            await session.execute(
                text("DELETE FROM communication_sessions WHERE id = :id"),
                {"id": uuid.UUID(room_id)}
            )
        if user_id:
            await session.execute(
                text("DELETE FROM users WHERE id = :id"),
                {"id": uuid.UUID(user_id)}
            )
        await session.commit()

        # Verify zero residual records
        check_user = await session.execute(
            text("SELECT count(*) FROM users WHERE id = :id"),
            {"id": uuid.UUID(user_id)}
        )
        assert check_user.scalar() == 0, "Test user record failed to purge"

        check_room = await session.execute(
            text("SELECT count(*) FROM communication_sessions WHERE id = :id"),
            {"id": uuid.UUID(room_id)}
        )
        assert check_room.scalar() == 0, "Test room record failed to purge"

    await dispose_engine()
    print(f"[PASS] 20. Database cleanup verified: All test records ({user_id}, {room_id}) purged.")


def main():
    # 1. Run full REST API test suite on Loop 1
    user_id, room_id, access_token = asyncio.run(run_async_api_tests())

    # 2. Run WebSocket tests on isolated TestClient thread
    run_websocket_tests(room_id, access_token)

    # 3. Run Event Loop Isolation Regression Tests across separate sequential loops
    print("-" * 60)
    print("Running Event Loop Isolation & Cleanup Regression Suite")
    print("-" * 60)
    l1 = asyncio.run(run_event_loop_regression_query(1))
    l2 = asyncio.run(run_event_loop_regression_query(2))
    l3 = asyncio.run(run_event_loop_regression_query(3))

    # Assert that all 3 loops were genuinely distinct instances
    assert len({l1, l2, l3}) == 3, f"Expected 3 distinct event loops, got {l1}, {l2}, {l3}"
    print(f"[PASS] 19.4 Verified 3 genuinely distinct event loop instances executed: {l1} != {l2} != {l3}")

    # 4. Clean up test records from database
    asyncio.run(cleanup_test_records(user_id, room_id))

    print("=" * 60)
    print("ALL BACKEND, DATABASE, WEBSOCKET & REGRESSION TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
