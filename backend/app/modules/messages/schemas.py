from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class MessageCreate(BaseModel):
    room_id: str
    content: str = Field(..., min_length=1)
    input_method: Optional[str] = "EYE_BLINK"
    morse_raw: Optional[str] = ""
    confidence_score: Optional[float] = 1.00


class MessageResponse(BaseModel):
    id: str
    room_id: str
    user_id: str
    content: str
    input_method: str
    morse_raw: str = ""
    confidence_score: str = "1.00"
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        return str(v) if v is not None else ""

    class Config:
        from_attributes = True
