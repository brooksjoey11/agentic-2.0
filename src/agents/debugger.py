"""Debugger agent — analyses errors and suggests fixes."""
from typing import Any

from src.agents.base import BaseAgent


class DebuggerAgent(BaseAgent):
    """Identifies bugs and proposes corrective actions."""

    async def run(self, task: dict[str, Any]) -> dict[str, Any]:
        error = task.get("error", "")
        fix = ""
        return {"error": error, "suggested_fix": fix}
