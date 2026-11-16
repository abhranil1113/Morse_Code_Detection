import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.models.communication_event import CommunicationEvent
from app.modules.messages.schemas import MessageCreate, MessageResponse
from app.modules.messages.repository import MessageRepository
from app.modules.rooms.repository import RoomRepository
from app.websocket.manager import ws_manager


class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MessageRepository(db)
        self.room_repo = RoomRepository(db)

    async def create_message(self, message_in: MessageCreate, user_id: uuid.UUID) -> MessageResponse:
        try:
            session_uuid = uuid.UUID(message_in.room_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid room_id UUID format")

        session = await self.room_repo.get_by_id(session_uuid)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target communication room not found")

        conf_dec = Decimal(str(round(message_in.confidence_score, 4))) if message_in.confidence_score is not None else Decimal("1.0000")

        msg = Message(
            id=uuid.uuid4(),
            communication_session_id=session_uuid,
            sender_user_id=user_id,
            content=message_in.content.strip(),
            input_method=message_in.input_method or "EYE_BLINK",
            morse_code=message_in.morse_raw or "",
            confidence=conf_dec
        )
        created_message = await self.repo.create(msg)

        # Log event in communication_events table
        event = CommunicationEvent(
            id=uuid.uuid4(),
            communication_session_id=session_uuid,
            user_id=user_id,
            event_type="MESSAGE_COMMITTED",
            duration_ms=None,
            confidence=conf_dec,
            metadata_json={
                "content": created_message.content,
                "input_method": created_message.input_method,
                "morse_code": created_message.morse_code
            },
            occurred_at=datetime.now(timezone.utc)
        )
        await self.repo.log_event(event)

        response_payload = MessageResponse(
            id=str(created_message.id),
            room_id=str(created_message.communication_session_id),
            user_id=str(created_message.sender_user_id),
            content=created_message.content,
            input_method=created_message.input_method,
            morse_raw=created_message.morse_code or "",
            confidence_score=str(created_message.confidence or "1.00"),
            created_at=created_message.created_at
        )

        # Broadcast in real-time to active WebSocket subscribers in this room
        try:
            await ws_manager.broadcast_to_room(
                str(session_uuid),
                {
                    "type": "NEW_MESSAGE",
                    "data": {
                        "id": response_payload.id,
                        "room_id": response_payload.room_id,
                        "user_id": response_payload.user_id,
                        "content": response_payload.content,
                        "input_method": response_payload.input_method,
                        "morse_raw": response_payload.morse_raw,
                        "confidence_score": response_payload.confidence_score,
                        "created_at": response_payload.created_at.isoformat()
                    }
                }
            )
        except Exception:
            pass

        return response_payload

    async def get_room_messages(self, room_id: str, limit: int = 50) -> List[MessageResponse]:
        messages = await self.repo.list_by_room(room_id, limit=limit)
        return [
            MessageResponse(
                id=str(m.id),
                room_id=str(m.communication_session_id),
                user_id=str(m.sender_user_id),
                content=m.content,
                input_method=m.input_method,
                morse_raw=m.morse_code or "",
                confidence_score=str(m.confidence or "1.00"),
                created_at=m.created_at
            )
            for m in messages
        ]
