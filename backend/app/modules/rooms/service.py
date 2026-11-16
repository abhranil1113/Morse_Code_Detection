import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication_session import CommunicationSession
from app.models.session_participant import SessionParticipant
from app.modules.rooms.schemas import RoomCreate, RoomResponse, RoomMemberAdd, RoomMemberResponse
from app.modules.rooms.repository import RoomRepository


class RoomService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RoomRepository(db)

    async def create_room(self, room_in: RoomCreate, creator_user_id: uuid.UUID) -> RoomResponse:
        existing = await self.repo.get_by_name(room_in.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A room / communication session with this name already exists"
            )

        session_id = uuid.uuid4()
        settings_dict = room_in.settings or {}
        if room_in.description:
            settings_dict["description"] = room_in.description

        session = CommunicationSession(
            id=session_id,
            title=room_in.name.strip(),
            status="ACTIVE",
            settings=settings_dict,
            created_by_user_id=creator_user_id
        )
        created_session = await self.repo.create(session)

        # Creator automatically joins as facilitator/speaker
        participant = SessionParticipant(
            id=uuid.uuid4(),
            communication_session_id=created_session.id,
            user_id=creator_user_id,
            participant_role="SPEAKER",
            status="JOINED"
        )
        await self.repo.add_participant(participant)

        return RoomResponse(
            id=str(created_session.id),
            name=created_session.title or "Room",
            description=created_session.settings.get("description", ""),
            status=created_session.status,
            created_by=str(created_session.created_by_user_id) if created_session.created_by_user_id else None,
            created_at=created_session.created_at
        )

    async def list_rooms(self, skip: int = 0, limit: int = 100) -> List[RoomResponse]:
        sessions = await self.repo.list_all(skip=skip, limit=limit)
        return [
            RoomResponse(
                id=str(s.id),
                name=s.title or "Room",
                description=s.settings.get("description", "") if s.settings else "",
                status=s.status,
                created_by=str(s.created_by_user_id) if s.created_by_user_id else None,
                created_at=s.created_at
            )
            for s in sessions
        ]

    async def get_room(self, room_id: str) -> RoomResponse:
        session = await self.repo.get_by_id(room_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
        return RoomResponse(
            id=str(session.id),
            name=session.title or "Room",
            description=session.settings.get("description", "") if session.settings else "",
            status=session.status,
            created_by=str(session.created_by_user_id) if session.created_by_user_id else None,
            created_at=session.created_at
        )

    async def join_room(self, room_id: str, user_id: uuid.UUID, role: str = "SPEAKER") -> RoomMemberResponse:
        session = await self.repo.get_by_id(room_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

        existing_part = await self.repo.get_participant(session.id, user_id)
        if existing_part:
            # Re-activate status if previously left
            await self.repo.update_participant_status(session.id, user_id, "JOINED", left_at=None)
            return RoomMemberResponse(
                id=str(existing_part.id),
                room_id=str(session.id),
                user_id=str(user_id),
                role=existing_part.participant_role,
                status="JOINED",
                joined_at=existing_part.joined_at
            )

        new_part = SessionParticipant(
            id=uuid.uuid4(),
            communication_session_id=session.id,
            user_id=user_id,
            participant_role=role.upper() if role else "SPEAKER",
            status="JOINED"
        )
        created_part = await self.repo.add_participant(new_part)
        return RoomMemberResponse(
            id=str(created_part.id),
            room_id=str(session.id),
            user_id=str(user_id),
            role=created_part.participant_role,
            status=created_part.status,
            joined_at=created_part.joined_at
        )

    async def leave_room(self, room_id: str, user_id: uuid.UUID) -> dict:
        session = await self.repo.get_by_id(room_id)
        if session:
            await self.repo.update_participant_status(
                session.id, user_id, "LEFT", left_at=datetime.now(timezone.utc)
            )
        return {"detail": "Left room successfully"}

    async def get_room_members(self, room_id: str) -> List[RoomMemberResponse]:
        participants = await self.repo.get_participants(room_id)
        return [
            RoomMemberResponse(
                id=str(p.id),
                room_id=str(p.communication_session_id),
                user_id=str(p.user_id),
                role=p.participant_role,
                status=p.status,
                joined_at=p.joined_at
            )
            for p in participants
        ]

    async def end_room(self, room_id: str, user_id: uuid.UUID) -> dict:
        session = await self.repo.get_by_id(room_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
        await self.repo.end_session(session.id)
        return {"detail": "Room ended successfully", "status": "COMPLETED"}
