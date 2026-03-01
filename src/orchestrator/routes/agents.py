"""Agent management routes."""
from fastapi import APIRouter, Depends

from src.orchestrator.dependencies import get_current_user
from src.orchestrator.models.agent import Agent, AgentCreate

router = APIRouter()


@router.get("/")
async def list_agents(current_user: dict = Depends(get_current_user)) -> list[dict]:
    return []


@router.post("/", status_code=201)
async def create_agent(
    payload: AgentCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return {"id": "new-agent-id", **payload.model_dump()}


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return {"id": agent_id}


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_user),
) -> None:
    pass
