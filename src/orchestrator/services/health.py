"""Health service logic."""


async def get_health() -> dict:
    return {"status": "ok", "services": {}}
