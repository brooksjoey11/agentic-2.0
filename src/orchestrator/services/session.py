"""Session service logic."""
from src.orchestrator.models.session import Session, SessionCreate


async def create_session(payload: SessionCreate) -> Session:
    return Session(id="placeholder", **payload.model_dump())


async def get_session(session_id: str) -> Session | None:
    return None


async def list_sessions() -> list[Session]:
    return []


async def delete_session(session_id: str) -> bool:
    return True
