"""Session Pydantic models."""
from pydantic import BaseModel

from src.orchestrator.models.common import TimestampMixin


class SessionCreate(BaseModel):
    name: str
    description: str = ""


class Session(TimestampMixin):
    id: str
    name: str
    description: str = ""
    status: str = "active"
