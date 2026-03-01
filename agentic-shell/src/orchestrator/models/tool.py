"""
Tool Models
Pydantic models for tool management
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ToolType(str, Enum):
    """Tool type enumeration"""
    SYSTEM = "system"
    CLOUD = "cloud"
    API = "api"
    CUSTOM = "custom"


class ToolInfo(BaseModel):
    """Tool information model"""
    name: str
    type: ToolType
    description: str
    version: str
    enabled: bool
    commands: List[str] = Field(default_factory=list)
    rate_limit: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolExecution(BaseModel):
    """Tool execution record"""
    id: str
    tool_name: str
    arguments: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    status: str  # pending, running, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ToolResult(BaseModel):
    """Tool execution result"""
    success: bool
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    returncode: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int


class ToolRegistry(BaseModel):
    """Tool registry configuration"""
    tools: Dict[str, ToolInfo]
    default_timeout: int = 300
    max_output_size: int = 1048576  # 1MB