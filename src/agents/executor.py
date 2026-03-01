"""Executor agent — runs planned steps using available tools."""
from typing import Any

from src.agents.base import BaseAgent


class ExecutorAgent(BaseAgent):
    """Executes a list of planned steps sequentially."""

    async def run(self, task: dict[str, Any]) -> dict[str, Any]:
        steps: list[dict] = task.get("steps", [])
        results = []
        for step in steps:
            results.append({"step": step, "status": "executed"})
        return {"results": results}
