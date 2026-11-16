import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
try:
    from jose import JWTError, jwt
except ImportError:
    import jwt
    from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.db_connection import get_db
from app.models.user import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import TokenData

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)

DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    repo = UserRepository(db)

    if not token:
        # Fallback anonymous/demo user for development & instant local testability
        demo_user = await repo.get_by_email("demo@eyespeak.ai")
        if demo_user:
            return demo_user

        # Create demo user on the fly if not yet in database
        demo = User(
            id=DEMO_USER_ID,
            display_name="Demo User",
            email="demo@eyespeak.ai",
            password_hash="demo_hashed_placeholder",
            role="USER",
            is_active=True
        )
        try:
            created = await repo.create(demo)
            return created
        except Exception:
            # In case concurrent creation occurred
            user = await repo.get_by_email("demo@eyespeak.ai")
            if user:
                return user
            raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise credentials_exception
        token_data = TokenData(user_id=user_id_str)
    except JWTError:
        raise credentials_exception

    user = await repo.get_by_id(token_data.user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user
