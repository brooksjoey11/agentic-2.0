"""Reflector agent — evaluates outcomes and refines strategy."""
from typing import Any

from src.agents.base import BaseAgent


class ReflectorAgent(BaseAgent):
    """Reviews task outcomes and feeds insights back to the planner."""

    async def run(self, task: dict[str, Any]) -> dict[str, Any]:
        outcome = task.get("outcome", {})
        insights: list[str] = []
        return {"outcome": outcome, "insights": insights}
