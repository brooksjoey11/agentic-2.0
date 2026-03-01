"""Tool registry — discover and manage available tools."""
from typing import Any, Callable

_registry: dict[str, Callable[..., Any]] = {}


def register(name: str) -> Callable:
    """Decorator to register a tool function by name."""
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        _registry[name] = fn
        return fn
    return decorator


def get_tool(name: str) -> Callable[..., Any] | None:
    return _registry.get(name)


def list_tools() -> list[str]:
    return list(_registry.keys())
