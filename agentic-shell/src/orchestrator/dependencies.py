"""
Dependency Injection
FastAPI dependencies for service injection
"""

from functools import lru_cache
from typing import Optional

from .services.health import HealthService
from .services.session import SessionService
from .services.agent import AgentService
from .services.tool import ToolService
from .services.metrics import MetricsService
from .services.queue import QueueService
from .db.database import get_db_pool
from .cache.redis import get_redis_client
from .messaging.rabbitmq import get_rabbitmq_channel
from .config import config


@lru_cache()
def get_health_service() -> HealthService:
    """Get health service instance"""
    return HealthService()


@lru_cache()
def get_session_service() -> SessionService:
    """Get session service instance"""
    return SessionService(
        db_pool=get_db_pool(),
        redis=get_redis_client(),
        queue=get_rabbitmq_channel()
    )


@lru_cache()
def get_agent_service() -> AgentService:
    """Get agent service instance"""
    return AgentService(
        redis=get_redis_client(),
        queue=get_rabbitmq_channel()
    )


@lru_cache()
def get_tool_service() -> ToolService:
    """Get tool service instance"""
    return ToolService(
        db_pool=get_db_pool(),
        redis=get_redis_client()
    )


@lru_cache()
def get_metrics_service() -> MetricsService:
    """Get metrics service instance"""
    return MetricsService(
        db_pool=get_db_pool(),
        redis=get_redis_client()
    )


@lru_cache()
def get_queue_service() -> QueueService:
    """Get queue service instance"""
    return QueueService(
        redis=get_redis_client(),
        channel=get_rabbitmq_channel()
    )