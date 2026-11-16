import uuid
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.communication_session import CommunicationSession
from app.models.session_participant import SessionParticipant


class RoomRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, session: CommunicationSession) -> CommunicationSession:
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def get_by_id(self, session_id: uuid.UUID | str) -> Optional[CommunicationSession]:
        if isinstance(session_id, str):
            try:
                session_id = uuid.UUID(session_id)
            except ValueError:
                return None
        result = await self.db.execute(
            select(CommunicationSession).where(CommunicationSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[CommunicationSession]:
        result = await self.db.execute(
            select(CommunicationSession).where(CommunicationSession.title == name.strip())
        )
        return result.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[CommunicationSession]:
        result = await self.db.execute(
            select(CommunicationSession)
            .order_by(CommunicationSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_participant(self, participant: SessionParticipant) -> SessionParticipant:
        self.db.add(participant)
        await self.db.flush()
        await self.db.refresh(participant)
        return participant

    async def get_participant(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[SessionParticipant]:
        result = await self.db.execute(
            select(SessionParticipant).where(
                SessionParticipant.communication_session_id == session_id,
                SessionParticipant.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_participants(self, session_id: uuid.UUID | str) -> List[SessionParticipant]:
        if isinstance(session_id, str):
            try:
                session_id = uuid.UUID(session_id)
            except ValueError:
                return []
        result = await self.db.execute(
            select(SessionParticipant)
            .where(SessionParticipant.communication_session_id == session_id)
            .order_by(SessionParticipant.joined_at.asc())
        )
        return list(result.scalars().all())

    async def update_participant_status(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        status: str,
        left_at: Optional[datetime] = None
    ) -> None:
        values = {"status": status}
        if left_at is not None:
            values["left_at"] = left_at
        await self.db.execute(
            update(SessionParticipant)
            .where(
                SessionParticipant.communication_session_id == session_id,
                SessionParticipant.user_id == user_id
            )
            .values(**values)
        )
        await self.db.flush()

    async def end_session(self, session_id: uuid.UUID) -> None:
        await self.db.execute(
            update(CommunicationSession)
            .where(CommunicationSession.id == session_id)
            .values(status="COMPLETED", ended_at=datetime.now(timezone.utc))
        )
        await self.db.flush()
