"""Base agent abstract class."""
from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Abstract base class for all agentic-shell agents."""

    def __init__(self, name: str, config: dict[str, Any] | None = None) -> None:
        self.name = name
        self.config: dict[str, Any] = config or {}

    @abstractmethod
    async def run(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a task and return the result."""

    async def on_start(self) -> None:
        """Lifecycle hook called before the agent starts running."""

    async def on_stop(self) -> None:
        """Lifecycle hook called after the agent has stopped."""
