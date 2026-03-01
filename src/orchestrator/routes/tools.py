"""Tool management routes."""
from fastapi import APIRouter, Depends

from src.orchestrator.dependencies import get_current_user
from src.orchestrator.models.tool import Tool, ToolCreate

router = APIRouter()


@router.get("/")
async def list_tools(current_user: dict = Depends(get_current_user)) -> list[dict]:
    return []


@router.post("/", status_code=201)
async def register_tool(
    payload: ToolCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return {"id": "new-tool-id", **payload.model_dump()}


@router.get("/{tool_id}")
async def get_tool(
    tool_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return {"id": tool_id}
