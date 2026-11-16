import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Determine pool class: In testing environments, NullPool prevents pooled asyncpg connections
# from leaking or being shared across distinct asyncio event loops.
# In production, default QueuePool provides connection pooling.
is_test_mode = settings.TESTING or os.getenv("TESTING", "").lower() in ("1", "true", "yes")

engine_kwargs = {
    "echo": False,
    "future": True,
}

if is_test_mode:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20
    })

# Async Engine for high-performance FastAPI requests & WebSockets
engine = create_async_engine(
    settings.async_database_url,
    **engine_kwargs
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# Base ORM model
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engine() -> None:
    """Explicitly close all connections in engine connection pool."""
    await engine.dispose()
