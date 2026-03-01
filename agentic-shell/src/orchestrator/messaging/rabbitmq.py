"""
RabbitMQ Module
Message queue connection and utilities
"""

import aio_pika
from typing import Optional
from functools import lru_cache

from ..config import config


class RabbitMQChannel:
    """RabbitMQ channel wrapper"""
    
    def __init__(self):
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.RobustChannel] = None
    
    async def initialize(self):
        """Initialize RabbitMQ connection and channel"""
        self._connection = await aio_pika.connect_robust(
            config.rabbitmq.url,
            heartbeat=60,
            timeout=30
        )
        
        self._channel = await self._connection.channel()
        self._channel.prefetch_count = 10
        
        # Declare exchanges
        await self._channel.declare_exchange(
            "agent_exchange",
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        
        await self._channel.declare_exchange(
            "control_exchange",
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        
        await self._channel.declare_exchange(
            "response_exchange",
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        
        # Declare queues
        agent_types = ["planner", "executor", "coder", "debugger", "optimizer", "reflector"]
        for agent_type in agent_types:
            queue = await self._channel.declare_queue(
                f"agent.{agent_type}",
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "dead.letter.exchange",
                    "x-max-retries": 3
                }
            )
            await queue.bind("agent_exchange", f"agent.{agent_type}")
        
        # Declare dead letter queue
        dead_letter_queue = await self._channel.declare_queue(
            "dead.letter",
            durable=True
        )
        await dead_letter_queue.bind("dead.letter.exchange", "#")
        
        # Declare response queue
        response_queue = await self._channel.declare_queue(
            "agent.responses",
            durable=True
        )
        await response_queue.bind("response_exchange", "agent.responses")
    
    @property
    def channel(self) -> aio_pika.RobustChannel:
        """Get channel (initialized)"""
        if not self._channel:
            raise RuntimeError("RabbitMQ not initialized")
        return self._channel
    
    async def publish(self, exchange: str, routing_key: str, body: bytes):
        """Publish message to exchange"""
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json"
            ),
            routing_key=routing_key
        )
    
    async def declare_queue(self, name: str, durable: bool = True, passive: bool = False, arguments: dict = None):
        """Declare a queue"""
        return await self.channel.declare_queue(
            name,
            durable=durable,
            passive=passive,
            arguments=arguments or {}
        )
    
    async def get_queue(self, name: str):
        """Get queue by name"""
        return await self.channel.get_queue(name)
    
    async def close(self):
        """Close connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None


@lru_cache()
def get_rabbitmq_channel() -> RabbitMQChannel:
    """Get RabbitMQ channel singleton"""
    return RabbitMQChannel()


async def get_rabbitmq_connection() -> aio_pika.RobustConnection:
    """Get RabbitMQ connection (legacy)"""
    return await aio_pika.connect_robust(config.rabbitmq.url)