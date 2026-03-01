"""FastAPI application entry point for the orchestrator service."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.orchestrator.config import settings
from src.orchestrator.routes import agents, health, metrics, sessions, tools

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(tools.router, prefix="/tools", tags=["tools"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
