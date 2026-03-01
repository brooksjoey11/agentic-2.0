"""Task queue service (RabbitMQ-backed)."""
import json
from typing import Any

from src.orchestrator.messaging.rabbitmq import get_channel


async def enqueue_task(queue_name: str, payload: dict[str, Any]) -> None:
    channel = await get_channel()
    await channel.default_exchange.publish(
        message=json.dumps(payload).encode(),
        routing_key=queue_name,
    )
