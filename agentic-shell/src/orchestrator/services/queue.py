"""
Queue Service
Manages message queues for agent communication
"""

import json
import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import aio_pika

from ..cache.redis import RedisClient
from ..models.agent import AgentRequest, AgentResponse


class QueueService:
    """Service for managing message queues"""
    
    def __init__(self, redis: RedisClient, channel: aio_pika.Channel):
        self.redis = redis
        self.channel = channel
        self.consumers = {}
    
    async def publish_to_agent(self, agent_type: str, request: AgentRequest) -> None:
        """Publish message to agent queue"""
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(request.dict()).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
                timestamp=datetime.now()
            ),
            routing_key=f"agent.{agent_type}"
        )
        
        # Track queue depth in Redis
        await self.redis.incr(f"queue:depth:{agent_type}")
    
    async def publish_response(self, response: AgentResponse) -> None:
        """Publish agent response to results queue"""
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(response.dict()).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
                timestamp=datetime.now()
            ),
            routing_key="agent.responses"
        )
    
    async def start_consumer(self, queue_name: str, callback: Callable) -> None:
        """Start consuming messages from a queue"""
        queue = await self.channel.declare_queue(queue_name, durable=True)
        
        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    data = json.loads(message.body)
                    await callback(data)
                    
                    # Decrement queue depth
                    await self.redis.decr(f"queue:depth:{queue_name.replace('agent.', '')}")
                    
                except Exception as e:
                    # Log error and possibly dead-letter
                    print(f"Error processing message: {e}")
        
        await queue.consume(on_message)
        self.consumers[queue_name] = callback
    
    async def get_queue_depth(self, queue_name: str) -> int:
        """Get current depth of a queue"""
        queue = await self.channel.declare_queue(queue_name, durable=True, passive=True)
        return queue.declaration_result.message_count
    
    async def get_all_queue_depths(self) -> Dict[str, int]:
        """Get depths of all agent queues"""
        depths = {}
        agent_types = ["planner", "executor", "coder", "debugger", "optimizer", "reflector"]
        
        for agent_type in agent_types:
            depth = await self.get_queue_depth(f"agent.{agent_type}")
            depths[agent_type] = depth
            
            # Update Redis
            await self.redis.set(f"queue:depth:{agent_type}", depth)
        
        return depths
    
    async def purge_queue(self, queue_name: str) -> int:
        """Purge all messages from a queue"""
        queue = await self.channel.declare_queue(queue_name, durable=True, passive=True)
        count = await queue.purge()
        
        # Update Redis
        agent_type = queue_name.replace("agent.", "")
        await self.redis.set(f"queue:depth:{agent_type}", 0)
        
        return count
    
    async def move_to_dead_letter(self, message: aio_pika.IncomingMessage, error: str) -> None:
        """Move failed message to dead letter queue"""
        dead_letter_queue = await self.channel.declare_queue("dead.letter", durable=True)
        
        # Add error info to message
        body = json.loads(message.body)
        body["error"] = error
        body["failed_at"] = datetime.now().isoformat()
        
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
                timestamp=datetime.now()
            ),
            routing_key="dead.letter"
        )
    
    async def retry_dead_letter(self, message_id: str) -> None:
        """Retry a message from dead letter queue"""
        # In production, implement dead letter queue retry logic
        pass
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics"""
        depths = await self.get_all_queue_depths()
        
        # Get dead letter queue stats
        dead_letter = await self.channel.declare_queue("dead.letter", durable=True, passive=True)
        dead_letter_count = dead_letter.declaration_result.message_count
        
        return {
            "queue_depths": depths,
            "total_messages": sum(depths.values()),
            "dead_letter_count": dead_letter_count,
            "timestamp": datetime.now().isoformat()
        }
    
    async def close(self) -> None:
        """Close all consumers and channel"""
        for queue_name in self.consumers:
            # Would need to properly cancel consumers
            pass
        
        await self.channel.close()