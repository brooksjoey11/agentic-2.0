"""
Standard Metrics Collection
Provides consistent metrics across all services.
"""

import asyncio
import time
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge

# =============================================================================
# HTTP Metrics
# =============================================================================
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['service', 'method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['service', 'method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
)

# =============================================================================
# Agent Metrics
# =============================================================================
agent_tasks_total = Counter(
    'agent_tasks_total',
    'Total agent tasks',
    ['agent_type', 'status']
)

agent_task_duration_seconds = Histogram(
    'agent_task_duration_seconds',
    'Agent task duration',
    ['agent_type'],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60)
)

agent_queue_depth = Gauge(
    'agent_queue_depth',
    'Current queue depth',
    ['agent_type']
)

agent_memory_usage = Gauge(
    'agent_memory_usage_bytes',
    'Agent memory usage in bytes',
    ['agent_type']
)

agent_cpu_usage = Gauge(
    'agent_cpu_usage_percent',
    'Agent CPU usage percent',
    ['agent_type']
)

# =============================================================================
# Tool Metrics
# =============================================================================
tool_executions_total = Counter(
    'tool_executions_total',
    'Total tool executions',
    ['tool_name', 'status']
)

tool_execution_duration_seconds = Histogram(
    'tool_execution_duration_seconds',
    'Tool execution duration',
    ['tool_name'],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300)
)

# =============================================================================
# Queue Metrics
# =============================================================================
queue_messages_published = Counter(
    'queue_messages_published_total',
    'Total messages published',
    ['queue']
)

queue_messages_consumed = Counter(
    'queue_messages_consumed_total',
    'Total messages consumed',
    ['queue']
)

queue_messages_failed = Counter(
    'queue_messages_failed_total',
    'Total messages failed',
    ['queue', 'error_type']
)

# =============================================================================
# Database Metrics
# =============================================================================
db_queries_total = Counter(
    'db_queries_total',
    'Total database queries',
    ['type']
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1)
)

db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

db_connection_errors = Counter(
    'db_connection_errors_total',
    'Database connection errors'
)

# =============================================================================
# Cache Metrics
# =============================================================================
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache']
)

cache_hit_ratio = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio',
    ['cache']
)

# =============================================================================
# Dead Letter Queue Metrics
# =============================================================================
dlq_messages = Counter(
    'dlq_messages_total',
    'Messages moved to dead letter queue',
    ['queue']
)

dlq_current_size = Gauge(
    'dlq_current_size',
    'Current dead letter queue size',
    ['queue']
)

# =============================================================================
# Decorators for automatic metrics
# =============================================================================

def measure_time(metric: Histogram):
    """Decorator to measure function duration."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                metric.observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                metric.observe(duration)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def count_calls(counter: Counter, **labels):
    """Decorator to count function calls."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                counter.labels(**labels, status="success").inc()
                return result
            except Exception as e:
                counter.labels(**labels, status="error").inc()
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                counter.labels(**labels, status="success").inc()
                return result
            except Exception as e:
                counter.labels(**labels, status="error").inc()
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
