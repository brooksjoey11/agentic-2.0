"""Coder agent — generates code based on specifications."""
from typing import Any

from src.agents.base import BaseAgent


class CoderAgent(BaseAgent):
    """Generates source code from natural-language specifications."""

    async def run(self, task: dict[str, Any]) -> dict[str, Any]:
        spec = task.get("spec", "")
        code = ""
        return {"code": code, "spec": spec}
