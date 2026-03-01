"""
Common Models
Shared Pydantic models used across the application
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime


class Pagination(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: str = "desc"


class DateRange(BaseModel):
    """Date range for queries"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class Error(BaseModel):
    """Error response model"""
    code: str
    message: str
    details: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthStatus(BaseModel):
    """Health check status"""
    service: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: Optional[int] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class VersionInfo(BaseModel):
    """Version information"""
    version: str
    build_date: str
    git_commit: str
    python_version: str


class ResourceQuota(BaseModel):
    """Resource quota limits"""
    cpu_limit: float
    memory_limit_mb: int
    max_sessions: int
    max_concurrent_tools: int
    rate_limit_requests: int
    rate_limit_period: int