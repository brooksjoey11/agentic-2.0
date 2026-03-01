"""Worker agent — consumes tasks from the queue and dispatches them."""
import asyncio
import json
import logging
from typing import Any

import aio_pika

from src.agents.base import BaseAgent
from src.orchestrator.config import settings

logger = logging.getLogger(__name__)


class WorkerAgent(BaseAgent):
    """Listens on a RabbitMQ queue and executes tasks."""

    QUEUE_NAME = "agentic.tasks"

    async def run(self, task: dict[str, Any]) -> dict[str, Any]:
        logger.info("Processing task: %s", task)
        return {"status": "completed", "task": task}

    async def start_consuming(self) -> None:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue(self.QUEUE_NAME, durable=True)
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        task = json.loads(message.body)
                        await self.run(task)


async def _main() -> None:
    worker = WorkerAgent(name="default-worker")
    await worker.on_start()
    await worker.start_consuming()


if __name__ == "__main__":
    asyncio.run(_main())
