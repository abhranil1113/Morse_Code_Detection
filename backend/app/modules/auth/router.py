from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_connection import get_db
from app.modules.auth.schemas import (
    UserCreate,
    UserLogin,
    Token,
    RefreshTokenRequest,
    UserResponse
)
from app.modules.auth.service import AuthService
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Creates a new user profile with a unique email and display name. Password is securely hashed using Bcrypt."
)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.register(user_in)


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate and receive JWT tokens",
    description="Authenticates with email or username and password. Issues a short-lived access token and a long-lived refresh token persisted as a SHA-256 hash in `auth_sessions`."
)
async def login(login_in: UserLogin, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.login(login_in)


@router.post(
    "/refresh",
    response_model=Token,
    summary="Rotate tokens via Refresh Token",
    description="Validates the submitted refresh token against `auth_sessions`, revokes the old session, and issues a newly rotated access token and refresh token pair."
)
async def refresh_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.refresh_tokens(payload.refresh_token)


@router.post(
    "/logout",
    summary="Revoke refresh token session",
    description="Marks the submitted refresh token session as revoked in the database, preventing future token rotations."
)
async def logout(
    payload: Optional[RefreshTokenRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    if payload and payload.refresh_token:
        try:
            service = AuthService(db)
            return await service.logout(payload.refresh_token)
        except Exception:
            pass
    return {"detail": "Logged out successfully"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the profile details of the user associated with the provided Bearer token."
)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.display_name,
        display_name=current_user.display_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )
