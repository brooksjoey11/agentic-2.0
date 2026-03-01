"""RabbitMQ messaging client (aio-pika)."""
import aio_pika

from src.orchestrator.config import settings

_connection: aio_pika.RobustConnection | None = None


async def get_connection() -> aio_pika.RobustConnection:
    global _connection
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    return _connection


async def get_channel() -> aio_pika.Channel:
    connection = await get_connection()
    return await connection.channel()


async def close_connection() -> None:
    global _connection
    if _connection and not _connection.is_closed:
        await _connection.close()
        _connection = None
