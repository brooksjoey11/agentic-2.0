"""Metrics routes (Prometheus exposition)."""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter()


@router.get("/", response_class=PlainTextResponse)
async def prometheus_metrics() -> str:
    return generate_latest().decode("utf-8")
