"""
Metrics Service
Collects and aggregates system metrics
"""

import json
from typing import Dict, List, Any
from datetime import datetime, timedelta
from prometheus_client import Counter, Histogram, Gauge

from ..db.database import DatabasePool
from ..cache.redis import RedisClient


# Prometheus metrics
REQUESTS_TOTAL = Counter('orchestrator_requests_total', 'Total requests', ['endpoint', 'method', 'status'])
RESPONSE_TIME = Histogram('orchestrator_response_time_seconds', 'Response time', ['endpoint'])
ACTIVE_CONNECTIONS = Gauge('orchestrator_active_connections', 'Active WebSocket connections')
QUEUE_DEPTH = Gauge('orchestrator_queue_depth', 'Queue depth', ['queue'])
AGENT_TASKS = Counter('orchestrator_agent_tasks_total', 'Agent tasks', ['agent_type', 'status'])
TOOL_EXECUTIONS = Counter('orchestrator_tool_executions_total', 'Tool executions', ['tool_name', 'status'])
ERROR_COUNT = Counter('orchestrator_errors_total', 'Errors', ['type'])


class MetricsService:
    """Service for collecting and aggregating metrics"""
    
    def __init__(self, db_pool: DatabasePool, redis: RedisClient):
        self.db_pool = db_pool
        self.redis = redis
    
    async def get_summary(self) -> Dict[str, Any]:
        """Get summary of all key metrics"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Gather metrics concurrently
        import asyncio
        results = await asyncio.gather(
            self.get_agent_metrics(hour_ago, now),
            self.get_tool_metrics(hour_ago, now),
            self.get_session_metrics(),
            self.get_queue_metrics(),
            self.get_error_metrics(day_ago, now),
            return_exceptions=True
        )
        
        return {
            "timestamp": now.isoformat(),
            "agents": results[0] if not isinstance(results[0], Exception) else {},
            "tools": results[1] if not isinstance(results[1], Exception) else {},
            "sessions": results[2] if not isinstance(results[2], Exception) else {},
            "queues": results[3] if not isinstance(results[3], Exception) else {},
            "errors": results[4] if not isinstance(results[4], Exception) else {},
        }
    
    async def get_agent_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get agent performance metrics"""
        # In production, query time-series database
        # For now, return from Redis
        metrics = {}
        
        agent_types = ["planner", "executor", "coder", "debugger", "optimizer", "reflector"]
        
        for agent_type in agent_types:
            completed = await self.redis.get(f"metrics:agent:{agent_type}:completed") or 0
            failed = await self.redis.get(f"metrics:agent:{agent_type}:failed") or 0
            
            metrics[agent_type] = {
                "tasks_completed": int(completed),
                "tasks_failed": int(failed),
                "total_tasks": int(completed) + int(failed),
                "error_rate": (int(failed) / (int(completed) + int(failed)) * 100) if (int(completed) + int(failed)) > 0 else 0
            }
        
        return metrics
    
    async def get_tool_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get tool usage metrics"""
        # Query tool executions from database
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    tool_name,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(duration_ms) as avg_duration
                FROM tool_executions
                WHERE created_at BETWEEN $1 AND $2
                GROUP BY tool_name
            """, start_time, end_time)
            
            return {
                row['tool_name']: {
                    "total": row['total'],
                    "successful": row['successful'],
                    "failed": row['failed'],
                    "avg_duration_ms": row['avg_duration']
                }
                for row in rows
            }
    
    async def get_session_metrics(self) -> Dict[str, Any]:
        """Get session metrics"""
        async with self.db_pool.acquire() as conn:
            # Total sessions
            total = await conn.fetchval("SELECT COUNT(*) FROM sessions")
            
            # Active sessions (last 5 minutes)
            active = await conn.fetchval("""
                SELECT COUNT(*) FROM sessions 
                WHERE last_active > NOW() - INTERVAL '5 minutes'
            """)
            
            # Average messages per session
            avg_messages = await conn.fetchval("""
                SELECT AVG(msg_count) FROM (
                    SELECT COUNT(*) as msg_count 
                    FROM conversations 
                    GROUP BY session_id
                ) as counts
            """) or 0
            
            return {
                "total_sessions": total,
                "active_sessions": active,
                "avg_messages_per_session": float(avg_messages)
            }
    
    async def get_queue_metrics(self) -> Dict[str, Any]:
        """Get queue depth metrics"""
        # In production, query RabbitMQ API
        # For now, return from Redis
        metrics = {}
        
        agent_types = ["planner", "executor", "coder", "debugger", "optimizer", "reflector"]
        
        for agent_type in agent_types:
            depth = await self.redis.get(f"queue:depth:{agent_type}") or 0
            metrics[agent_type] = int(depth)
        
        return metrics
    
    async def get_error_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get error rate and distribution metrics"""
        async with self.db_pool.acquire() as conn:
            # Total requests
            total = await conn.fetchval("""
                SELECT COUNT(*) FROM conversations 
                WHERE created_at BETWEEN $1 AND $2
            """, start_time, end_time) or 1
            
            # Errors from tool executions
            tool_errors = await conn.fetchval("""
                SELECT COUNT(*) FROM tool_executions 
                WHERE status = 'failed'
                AND created_at BETWEEN $1 AND $2
            """, start_time, end_time) or 0
            
            # Errors by type
            error_types = await conn.fetch("""
                SELECT error, COUNT(*) as count
                FROM tool_executions
                WHERE status = 'failed'
                AND created_at BETWEEN $1 AND $2
                GROUP BY error
                ORDER BY count DESC
                LIMIT 10
            """, start_time, end_time)
            
            return {
                "total_requests": total,
                "total_errors": tool_errors,
                "error_rate": (tool_errors / total * 100),
                "top_errors": [
                    {"type": row['error'][:50], "count": row['count']}
                    for row in error_types
                ]
            }
    
    async def get_latency_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get latency metrics (p50, p95, p99)"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    tool_name,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as p50,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as p99
                FROM tool_executions
                WHERE created_at BETWEEN $1 AND $2
                GROUP BY tool_name
            """, start_time, end_time)
            
            return {
                row['tool_name']: {
                    "p50_ms": float(row['p50']),
                    "p95_ms": float(row['p95']),
                    "p99_ms": float(row['p99'])
                }
                for row in rows
            }
    
    def record_request(self, endpoint: str, method: str, status: int, duration: float) -> None:
        """Record HTTP request metrics"""
        REQUESTS_TOTAL.labels(endpoint=endpoint, method=method, status=status).inc()
        RESPONSE_TIME.labels(endpoint=endpoint).observe(duration)
    
    def record_connection(self, increment: bool = True) -> None:
        """Record WebSocket connection count"""
        if increment:
            ACTIVE_CONNECTIONS.inc()
        else:
            ACTIVE_CONNECTIONS.dec()
    
    def record_queue_depth(self, queue_name: str, depth: int) -> None:
        """Record queue depth"""
        QUEUE_DEPTH.labels(queue=queue_name).set(depth)
    
    def record_agent_task(self, agent_type: str, status: str) -> None:
        """Record agent task completion"""
        AGENT_TASKS.labels(agent_type=agent_type, status=status).inc()
    
    def record_tool_execution(self, tool_name: str, status: str) -> None:
        """Record tool execution"""
        TOOL_EXECUTIONS.labels(tool_name=tool_name, status=status).inc()
    
    def record_error(self, error_type: str) -> None:
        """Record error"""
        ERROR_COUNT.labels(type=error_type).inc()