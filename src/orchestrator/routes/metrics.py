"""
Metrics Routes
Exposes Prometheus metrics and custom application metrics
"""

from fastapi import APIRouter, Response, Depends
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from typing import Dict, Any
from datetime import datetime, timedelta

from ..services.metrics import MetricsService
from ..dependencies import get_metrics_service
from ..auth import require_admin

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_prometheus_metrics():
    """Get Prometheus-formatted metrics"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/summary")
async def get_metrics_summary(
    metrics_service: MetricsService = Depends(get_metrics_service),
    _: bool = Depends(require_admin)
) -> Dict[str, Any]:
    """Get summary of all key metrics (admin only)"""
    return await metrics_service.get_summary()


@router.get("/agents")
async def get_agent_metrics(
    hours: int = 24,
    metrics_service: MetricsService = Depends(get_metrics_service)
) -> Dict[str, Any]:
    """Get agent performance metrics"""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    return await metrics_service.get_agent_metrics(start_time, end_time)


@router.get("/tools")
async def get_tool_metrics(
    hours: int = 24,
    metrics_service: MetricsService = Depends(get_metrics_service)
) -> Dict[str, Any]:
    """Get tool usage metrics"""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    return await metrics_service.get_tool_metrics(start_time, end_time)


@router.get("/sessions")
async def get_session_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service)
) -> Dict[str, Any]:
    """Get session metrics"""
    return await metrics_service.get_session_metrics()


@router.get("/queues")
async def get_queue_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service)
) -> Dict[str, Any]:
    """Get queue depth and processing metrics"""
    return await metrics_service.get_queue_metrics()


@router.get("/errors")
async def get_error_metrics(
    hours: int = 24,
    metrics_service: MetricsService = Depends(get_metrics_service)
) -> Dict[str, Any]:
    """Get error rate and distribution metrics"""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    return await metrics_service.get_error_metrics(start_time, end_time)


@router.get("/latency")
async def get_latency_metrics(
    hours: int = 24,
    metrics_service: MetricsService = Depends(get_metrics_service)
) -> Dict[str, Any]:
    """Get latency metrics (p50, p95, p99)"""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    return await metrics_service.get_latency_metrics(start_time, end_time)