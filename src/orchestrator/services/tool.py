"""Tool service logic."""
from src.orchestrator.models.tool import Tool, ToolCreate


async def register_tool(payload: ToolCreate) -> Tool:
    return Tool(id="placeholder", **payload.model_dump())


async def get_tool(tool_id: str) -> Tool | None:
    return None


async def list_tools() -> list[Tool]:
    return []
