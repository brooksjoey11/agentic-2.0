"""
Health Check Routes
Provides health check endpoints for monitoring
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
import psutil
import time

from ..services.health import HealthService
from ..dependencies import get_health_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(
    health_service: HealthService = Depends(get_health_service)
) -> Dict[str, Any]:
    """
    Comprehensive health check endpoint
    
    Returns status of all critical services:
    - Database connectivity
    - Redis connectivity
    - RabbitMQ connectivity
    - etcd connectivity
    - Consul connectivity
    - Disk space
    - Memory usage
    """
    return await health_service.check_all()


@router.get("/live")
async def liveness_probe() -> Dict[str, str]:
    """Kubernetes liveness probe - simple check if process is alive"""
    return {"status": "alive", "timestamp": time.time()}


@router.get("/ready")
async def readiness_probe(
    health_service: HealthService = Depends(get_health_service)
) -> Dict[str, Any]:
    """
    Kubernetes readiness probe - checks if service is ready to accept traffic
    Returns 200 if all essential services are connected
    """
    status = await health_service.check_essential()
    return status


@router.get("/metrics/system")
async def system_metrics() -> Dict[str, Any]:
    """System resource metrics"""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage_percent": psutil.disk_usage('/').percent,
        "open_files": len(psutil.Process().open_files()),
        "connections": len(psutil.Process().connections()),
    }