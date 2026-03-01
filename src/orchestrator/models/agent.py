"""
Agent Models
Pydantic models for agent management
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    """Agent status enumeration"""
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"
    STARTING = "starting"
    STOPPING = "stopping"


class AgentType(str, Enum):
    """Agent type enumeration"""
    PLANNER = "planner"
    EXECUTOR = "executor"
    CODER = "coder"
    DEBUGGER = "debugger"
    OPTIMIZER = "optimizer"
    REFLECTOR = "reflector"


class AgentInfo(BaseModel):
    """Agent information model"""
    type: AgentType
    status: AgentStatus
    version: str
    host: str
    pid: int
    start_time: datetime
    last_heartbeat: datetime
    tasks_completed: int
    tasks_failed: int
    current_task: Optional[Dict[str, Any]] = None
    queue_size: int
    memory_usage_mb: float
    cpu_usage_percent: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentMetrics(BaseModel):
    """Agent metrics model"""
    agent_type: AgentType
    period_start: datetime
    period_end: datetime
    tasks_completed: int
    tasks_failed: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    tokens_used: int
    cost_estimate: float
    error_rate: float
    uptime_percentage: float


class AgentControl(BaseModel):
    """Agent control action"""
    action: str  # start, stop, restart, scale
    replicas: Optional[int] = None
    force: bool = False


class AgentHeartbeat(BaseModel):
    """Agent heartbeat payload"""
    agent_type: AgentType
    host: str
    pid: int
    status: AgentStatus
    current_task: Optional[str] = None
    queue_size: int
    memory_usage_mb: float
    cpu_usage_percent: float
    uptime_seconds: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)