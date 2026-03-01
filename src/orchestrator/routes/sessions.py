"""Session management routes."""
from fastapi import APIRouter, Depends

from src.orchestrator.dependencies import get_current_user
from src.orchestrator.models.session import Session, SessionCreate

router = APIRouter()


@router.get("/")
async def list_sessions(current_user: dict = Depends(get_current_user)) -> list[dict]:
    return []


@router.post("/", status_code=201)
async def create_session(
    payload: SessionCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return {"id": "new-session-id", **payload.model_dump()}


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return {"id": session_id}


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> None:
    pass
