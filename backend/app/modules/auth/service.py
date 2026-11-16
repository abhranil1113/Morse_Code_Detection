import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.modules.auth.schemas import UserCreate, UserLogin, Token, UserResponse
from app.modules.auth.repository import UserRepository, AuthSessionRepository
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    hash_token
)
from app.core.config import settings


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = AuthSessionRepository(db)

    async def register(self, user_in: UserCreate) -> UserResponse:
        uname = (user_in.username or user_in.display_name or user_in.email.split("@")[0]).strip()
        if not uname:
            uname = "User"

        existing_email = await self.user_repo.get_by_email(user_in.email.strip().lower())
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )

        existing_name = await self.user_repo.get_by_display_name(uname)
        if existing_name:
            # If default name conflicts, append unique suffix
            uname = f"{uname}_{uuid.uuid4().hex[:4]}"

        user = User(
            id=uuid.uuid4(),
            display_name=uname,
            email=user_in.email.strip().lower(),
            password_hash=get_password_hash(user_in.password),
            role=user_in.role or "USER",
            is_active=True
        )
        created_user = await self.user_repo.create(user)
        return UserResponse(
            id=str(created_user.id),
            email=created_user.email,
            username=created_user.display_name,
            display_name=created_user.display_name,
            role=created_user.role,
            is_active=created_user.is_active,
            created_at=created_user.created_at
        )

    async def login(self, login_in: UserLogin) -> Token:
        identifier = login_in.email or login_in.username
        if not identifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide username or email"
            )

        user = await self.user_repo.get_by_identifier(identifier)
        if not user or not verify_password(login_in.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username/email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        # Store hashed refresh token in auth_sessions table
        token_hash = hash_token(refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.session_repo.create_session(
            user_id=user.id,
            refresh_token_hash=token_hash,
            expires_at=expires_at
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user_id=str(user.id)
        )

    async def refresh_tokens(self, refresh_token_str: str) -> Token:
        token_hash = hash_token(refresh_token_str)
        session = await self.session_repo.get_by_token_hash(token_hash)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked refresh token"
            )

        if session.expires_at < datetime.now(timezone.utc):
            await self.session_repo.revoke_session(session.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )

        user = await self.user_repo.get_by_id(session.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Token rotation: revoke old session, create new
        await self.session_repo.revoke_session(session.id)

        new_access_token = create_access_token(subject=str(user.id))
        new_refresh_token = create_refresh_token(subject=str(user.id))
        new_token_hash = hash_token(new_refresh_token)
        new_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await self.session_repo.create_session(
            user_id=user.id,
            refresh_token_hash=new_token_hash,
            expires_at=new_expires_at
        )

        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            user_id=str(user.id)
        )

    async def logout(self, refresh_token_str: str) -> dict:
        token_hash = hash_token(refresh_token_str)
        session = await self.session_repo.get_by_token_hash(token_hash)
        if session:
            await self.session_repo.revoke_session(session.id)
        return {"detail": "Logged out successfully"}
