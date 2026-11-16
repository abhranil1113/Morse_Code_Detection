from typing import List
from fastapi import APIRouter, Depends, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_connection import get_db
from app.modules.rooms.schemas import RoomCreate, RoomResponse, RoomMemberAdd, RoomMemberResponse
from app.modules.rooms.service import RoomService
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/rooms", tags=["Rooms & Communication Sessions"])


@router.post(
    "",
    response_model=RoomResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a communication session / room",
    description="Creates a new real-time communication session with status `ACTIVE`. The creator is automatically registered as a participant with role `SPEAKER`."
)
async def create_room(
    room_in: RoomCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = RoomService(db)
    return await service.create_room(room_in, creator_user_id=current_user.id)


@router.get(
    "",
    response_model=List[RoomResponse],
    summary="List active communication rooms",
    description="Returns a paginated list of active multi-user communication channels."
)
async def list_rooms(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    service = RoomService(db)
    return await service.list_rooms(skip=skip, limit=limit)


@router.get(
    "/{room_id}",
    response_model=RoomResponse,
    summary="Get room details by ID",
    description="Retrieves session metadata, title, settings, and lifecycle status for a given session UUID."
)
async def get_room(
    room_id: str = Path(..., description="UUID of the communication session"),
    db: AsyncSession = Depends(get_db)
):
    service = RoomService(db)
    return await service.get_room(room_id)


@router.post(
    "/{room_id}/join",
    response_model=RoomMemberResponse,
    summary="Join communication session",
    description="Registers the authenticated user as an active participant (`SPEAKER`, `ASSISTANT`, or `OBSERVER`) in the specified session."
)
async def join_room(
    room_id: str = Path(..., description="UUID of the communication session"),
    member_in: RoomMemberAdd = RoomMemberAdd(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = RoomService(db)
    target_user_id = member_in.user_id if member_in.user_id else current_user.id
    return await service.join_room(room_id, target_user_id, role=member_in.role or "SPEAKER")


@router.post(
    "/{room_id}/members",
    response_model=RoomMemberResponse,
    summary="Add member to session (Alias)",
    description="Idempotent endpoint to join or re-activate participant membership in a session."
)
async def add_room_member(
    room_id: str = Path(..., description="UUID of the communication session"),
    member_in: RoomMemberAdd = RoomMemberAdd(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = RoomService(db)
    target_user_id = member_in.user_id if member_in.user_id else current_user.id
    return await service.join_room(room_id, target_user_id, role=member_in.role or "SPEAKER")


@router.post(
    "/{room_id}/leave",
    summary="Leave communication session",
    description="Marks the authenticated user's participant record as `LEFT` and records `left_at` timestamp."
)
async def leave_room(
    room_id: str = Path(..., description="UUID of the communication session"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = RoomService(db)
    return await service.leave_room(room_id, user_id=current_user.id)


@router.get(
    "/{room_id}/members",
    response_model=List[RoomMemberResponse],
    summary="List session participants",
    description="Returns all active and past participants for a specified communication session."
)
async def list_room_members(
    room_id: str = Path(..., description="UUID of the communication session"),
    db: AsyncSession = Depends(get_db)
):
    service = RoomService(db)
    return await service.get_room_members(room_id)


@router.post(
    "/{room_id}/end",
    summary="End communication session",
    description="Terminates the session, marks status as `COMPLETED`, and sets `ended_at` timestamp."
)
async def end_room(
    room_id: str = Path(..., description="UUID of the communication session"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = RoomService(db)
    return await service.end_room(room_id, user_id=current_user.id)
