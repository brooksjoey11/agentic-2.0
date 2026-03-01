"""Agent Pydantic models."""
from pydantic import BaseModel

from src.orchestrator.models.common import TimestampMixin


class AgentCreate(BaseModel):
    name: str
    type: str
    config: dict = {}


class Agent(TimestampMixin):
    id: str
    name: str
    type: str
    config: dict = {}
    status: str = "idle"
