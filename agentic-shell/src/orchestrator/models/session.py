"""
Session Models
Pydantic models for session management
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class Message(BaseModel):
    """Chat message model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str  # user, agent, system, tool
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class SessionCreate(BaseModel):
    """Session creation request"""
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ttl_days: int = 7


class Session(BaseModel):
    """Session model"""
    id: str
    user_id: Optional[str] = None
    agent_assignments: Dict[str, str] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    last_active: datetime
    expires_at: Optional[datetime] = None
    message_count: int = 0


class SessionSummary(BaseModel):
    """Session summary for listings"""
    id: str
    user_id: Optional[str]
    created_at: datetime
    last_active: datetime
    message_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionStats(BaseModel):
    """Session statistics"""
    total_sessions: int
    active_sessions: int
    avg_messages_per_session: float
    avg_session_duration_seconds: float
    top_users: List[Dict[str, Any]]