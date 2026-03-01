"""Tool Pydantic models."""
from pydantic import BaseModel

from src.orchestrator.models.common import TimestampMixin


class ToolCreate(BaseModel):
    name: str
    description: str = ""
    config: dict = {}


class Tool(TimestampMixin):
    id: str
    name: str
    description: str = ""
    config: dict = {}
    enabled: bool = True
