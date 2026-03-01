"""Client Package - CLI, WebSocket client, and Rich Terminal UI"""

from .cli import main, AgenticShellClient
from .rich_ui import RichTerminalUI, run_ui, main as rich_main

__all__ = ["main", "AgenticShellClient", "RichTerminalUI", "run_ui", "rich_main"]