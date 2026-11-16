from app.db.db_connection import Base, engine
from app.models.user import User
from app.models.auth_session import AuthSession
from app.models.communication_session import CommunicationSession
from app.models.session_participant import SessionParticipant
from app.models.message import Message
from app.models.communication_event import CommunicationEvent
from app.models.vision_calibration import VisionCalibration

__all__ = [
    "Base",
    "engine",
    "User",
    "AuthSession",
    "CommunicationSession",
    "SessionParticipant",
    "Message",
    "CommunicationEvent",
    "VisionCalibration",
    "init_db",
]


async def init_db() -> None:
    """Create all tables in the PostgreSQL database if they do not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
