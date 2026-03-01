"""WebSocket client for real-time communication with the orchestrator."""
import asyncio
import json
from typing import Any

import websockets


async def connect(uri: str, on_message: Any | None = None) -> None:
    """Connect to the orchestrator WebSocket endpoint and listen for events."""
    async with websockets.connect(uri) as websocket:
        async for raw_message in websocket:
            message = json.loads(raw_message)
            if on_message:
                await on_message(message)
            else:
                print(message)


async def send(uri: str, payload: dict[str, Any]) -> None:
    """Send a single JSON payload to the orchestrator."""
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps(payload))
