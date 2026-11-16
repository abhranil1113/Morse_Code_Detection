import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, description="User email address")
    username: Optional[str] = Field(None, max_length=120, description="Display name / username")
    display_name: Optional[str] = Field(None, max_length=120, description="Display name alias")
    password: str = Field(..., min_length=4, description="Password (at least 4 characters)")
    role: Optional[str] = "USER"

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Please provide a valid email address (e.g. user@example.com)")
        return v

    @field_validator("username", mode="before")
    @classmethod
    def resolve_username(cls, v, values):
        if not v:
            data = getattr(values, "data", {})
            return data.get("display_name") or ""
        return v


class UserLogin(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        return str(v) if v is not None else ""

    @field_validator("username", mode="before")
    @classmethod
    def fill_username(cls, v, values):
        if not v:
            # fallback to display_name or email
            data = getattr(values, "data", {})
            return data.get("display_name", "")
        return v

    class Config:
        from_attributes = True
