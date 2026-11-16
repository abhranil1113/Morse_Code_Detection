from typing import List
from fastapi import APIRouter, Depends, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_connection import get_db
from app.modules.messages.schemas import MessageCreate, MessageResponse
from app.modules.messages.service import MessageService
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send eye-spoken Morse message",
    description="Persists an eye-spoken message with Morse transcript and confidence score into PostgreSQL, records an audit event, and broadcasts the message in real-time to active WebSocket subscribers in that room."
)
async def create_message(
    message_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MessageService(db)
    return await service.create_message(message_in, user_id=current_user.id)


@router.get(
    "/room/{room_id}",
    response_model=List[MessageResponse],
    summary="Get room message history",
    description="Retrieves a list of messages sent in the specified communication room in chronological order."
)
async def get_room_messages(
    room_id: str = Path(..., description="UUID of the communication session"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of historical messages to return"),
    db: AsyncSession = Depends(get_db)
):
    service = MessageService(db)
    return await service.get_room_messages(room_id, limit=limit)


@router.get(
    "/{room_id}",
    response_model=List[MessageResponse],
    summary="Get room message history (Alias)",
    description="Alias endpoint for retrieving messages for a specified communication room."
)
async def get_messages_by_room_alias(
    room_id: str = Path(..., description="UUID of the communication session"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of historical messages to return"),
    db: AsyncSession = Depends(get_db)
):
    service = MessageService(db)
    return await service.get_room_messages(room_id, limit=limit)
