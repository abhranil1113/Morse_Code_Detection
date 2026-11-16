import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.message import Message
from app.models.communication_event import CommunicationEvent


class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, message: Message) -> Message:
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def list_by_room(self, room_id: uuid.UUID | str, limit: int = 50) -> List[Message]:
        if isinstance(room_id, str):
            try:
                room_id = uuid.UUID(room_id)
            except ValueError:
                return []
        result = await self.db.execute(
            select(Message)
            .where(Message.communication_session_id == room_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, message_id: uuid.UUID | str) -> Optional[Message]:
        if isinstance(message_id, str):
            try:
                message_id = uuid.UUID(message_id)
            except ValueError:
                return None
        result = await self.db.execute(select(Message).where(Message.id == message_id))
        return result.scalar_one_or_none()

    async def log_event(self, event: CommunicationEvent) -> CommunicationEvent:
        self.db.add(event)
        await self.db.flush()
        return event
