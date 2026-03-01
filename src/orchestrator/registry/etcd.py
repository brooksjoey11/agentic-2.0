"""etcd service registry client."""
from typing import Any

import httpx

from src.orchestrator.config import settings

BASE_URL = f"http://{settings.etcd_host}:{settings.etcd_port}/v3"


async def put(key: str, value: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(f"{BASE_URL}/kv/put", json={"key": key, "value": value})


async def get(key: str) -> Any:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/kv/range", json={"key": key})
        return response.json()
