"""Planner agent — breaks high-level goals into sub-tasks."""
from typing import Any

from src.agents.base import BaseAgent


class PlannerAgent(BaseAgent):
    """Decomposes a goal into an ordered list of executable steps."""

    async def run(self, task: dict[str, Any]) -> dict[str, Any]:
        goal = task.get("goal", "")
        steps: list[str] = []
        return {"plan": steps, "goal": goal}
