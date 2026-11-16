import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class RoomCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = ""
    settings: Optional[Dict[str, Any]] = None


class RoomResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    status: str = "ACTIVE"
    created_by: Optional[str] = None
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        return str(v) if v is not None else ""

    @field_validator("created_by", mode="before")
    @classmethod
    def convert_creator_to_str(cls, v):
        return str(v) if v is not None else None

    class Config:
        from_attributes = True


class RoomMemberAdd(BaseModel):
    user_id: Optional[str] = None
    role: Optional[str] = "SPEAKER"


class RoomMemberResponse(BaseModel):
    id: str
    room_id: str
    user_id: str
    role: str
    status: str
    joined_at: datetime

    @field_validator("id", "room_id", "user_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        return str(v) if v is not None else ""

    class Config:
        from_attributes = True


class SessionStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(ACTIVE|PAUSED|COMPLETED|CANCELLED)$")
