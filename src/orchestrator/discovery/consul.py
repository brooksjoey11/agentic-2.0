"""Consul service discovery client."""
from typing import Any

import httpx

from src.orchestrator.config import settings

BASE_URL = f"http://{settings.consul_host}:{settings.consul_port}/v1"


async def register_service(name: str, address: str, port: int) -> None:
    async with httpx.AsyncClient() as client:
        await client.put(
            f"{BASE_URL}/agent/service/register",
            json={"Name": name, "Address": address, "Port": port},
        )


async def discover_service(name: str) -> Any:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health/service/{name}")
        return response.json()
