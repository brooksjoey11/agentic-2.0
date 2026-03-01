"""
Agent Service
Manages agent registration, discovery, and coordination
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from ..models.agent import AgentInfo, AgentMetrics, AgentControl, AgentStatus, AgentHeartbeat
from ..cache.redis import RedisClient
from ..messaging.rabbitmq import RabbitMQChannel


class AgentService:
    """Service for managing agents"""
    
    def __init__(self, redis: RedisClient, queue: RabbitMQChannel):
        self.redis = redis
        self.queue = queue
        self.heartbeat_timeout = 30  # seconds
    
    async def register_agent(self, heartbeat: AgentHeartbeat) -> None:
        """Register or update agent status"""
        key = f"agent:{heartbeat.agent_type}:{heartbeat.host}:{heartbeat.pid}"
        
        await self.redis.setex(
            key,
            self.heartbeat_timeout * 2,
            heartbeat.json()
        )
        
        # Update agent set
        await self.redis.sadd("agents:active", f"{heartbeat.agent_type}:{heartbeat.host}:{heartbeat.pid}")
    
    async def list_agents(self) -> List[AgentInfo]:
        """List all registered agents"""
        active_keys = await self.redis.smembers("agents:active")
        agents = []
        
        for key in active_keys:
            data = await self.redis.get(f"agent:{key}")
            if data:
                heartbeat = AgentHeartbeat.parse_raw(data)
                
                # Check if still alive
                age = (datetime.now() - heartbeat.timestamp).total_seconds()
                status = heartbeat.status
                if age > self.heartbeat_timeout:
                    status = AgentStatus.OFFLINE
                
                agents.append(AgentInfo(
                    type=heartbeat.agent_type,
                    status=status,
                    version="2.0.0",  # Would come from config
                    host=heartbeat.host,
                    pid=heartbeat.pid,
                    start_time=heartbeat.timestamp - timedelta(seconds=heartbeat.uptime_seconds),
                    last_heartbeat=heartbeat.timestamp,
                    tasks_completed=await self._get_task_count(heartbeat.agent_type, "completed"),
                    tasks_failed=await self._get_task_count(heartbeat.agent_type, "failed"),
                    current_task=await self._get_current_task(heartbeat.agent_type),
                    queue_size=await self._get_queue_size(heartbeat.agent_type),
                    memory_usage_mb=heartbeat.memory_usage_mb,
                    cpu_usage_percent=heartbeat.cpu_usage_percent
                ))
        
        return agents
    
    async def get_agent(self, agent_type: str) -> Optional[AgentInfo]:
        """Get detailed information about a specific agent"""
        agents = await self.list_agents()
        for agent in agents:
            if agent.type == agent_type:
                return agent
        return None
    
    async def get_metrics(self, agent_type: str, start_time: datetime, end_time: datetime) -> AgentMetrics:
        """Get performance metrics for an agent"""
        # In production, this would query a time-series database
        # For now, return placeholder metrics
        return AgentMetrics(
            agent_type=agent_type,
            period_start=start_time,
            period_end=end_time,
            tasks_completed=await self._get_task_count(agent_type, "completed", start_time, end_time),
            tasks_failed=await self._get_task_count(agent_type, "failed", start_time, end_time),
            avg_response_time_ms=234,
            p95_response_time_ms=567,
            p99_response_time_ms=890,
            tokens_used=15000,
            cost_estimate=0.45,
            error_rate=3.2,
            uptime_percentage=99.8
        )
    
    async def control_agent(self, agent_type: str, control: AgentControl) -> Dict[str, Any]:
        """Send control command to agent(s)"""
        # Publish control message to agent queue
        await self.queue.publish(
            exchange="control_exchange",
            routing_key=f"control.{agent_type}",
            body=json.dumps({
                "action": control.action,
                "replicas": control.replicas,
                "force": control.force,
                "timestamp": datetime.now().isoformat()
            }).encode()
        )
        
        return {
            "action": control.action,
            "agent_type": agent_type,
            "status": "command_sent"
        }
    
    async def get_queue_depths(self) -> Dict[str, int]:
        """Get current queue depth for each agent type"""
        agent_types = ["planner", "executor", "coder", "debugger", "optimizer", "reflector"]
        depths = {}
        
        for agent_type in agent_types:
            depth = await self._get_queue_size(agent_type)
            depths[agent_type] = depth
        
        return depths
    
    async def _get_task_count(self, agent_type: str, status: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> int:
        """Get task count for agent (simplified)"""
        # In production, this would query a database
        key = f"metrics:agent:{agent_type}:{status}"
        count = await self.redis.get(key)
        return int(count) if count else 0
    
    async def _get_current_task(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """Get current task for agent (simplified)"""
        # In production, this would come from agent heartbeat
        return None
    
    async def _get_queue_size(self, agent_type: str) -> int:
        """Get queue size for agent type"""
        # In production, would query RabbitMQ
        # For now, return from Redis
        depth = await self.redis.get(f"queue:depth:{agent_type}")
        return int(depth) if depth else 0