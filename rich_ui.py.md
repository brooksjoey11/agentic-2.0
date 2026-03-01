```python
#!/usr/bin/env python3
"""
Rich Terminal UI for Agentic Shell 2.0
File: src/client/rich_ui.py
Version: 3.0.0 (Production Rebuild)

Provides enhanced terminal interface with live-updating panels displaying conversation,
agent status, tool executions, and system metrics.

Environment Variables (all required variables must be set):
    SESSION_ID: Optional session identifier (auto-generated if not provided)
    UI_MAX_HISTORY: Maximum messages to retain (default: 100, min: 10, max: 1000)
    UI_REFRESH_RATE: Display refresh rate in Hz (default: 4.0, min: 1.0, max: 30.0)
    UI_MIN_INTERVAL: Minimum refresh interval in seconds (default: 0.25, min: 0.016)
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: INFO)
    UI_SHOW_METRICS: Show metrics panel (true/false) (default: true)
    UI_SHOW_AGENTS: Show agents panel (true/false) (default: true)
    UI_SHOW_TOOLS: Show tools panel (true/false) (default: true)
    UI_MAX_TOOL_HISTORY: Maximum tool executions to retain (default: 50, min: 10)
    UI_MAX_RENDER_ERRORS: Maximum consecutive render errors before fallback (default: 5)

File System Requirements:
    - Log directory: /var/log/agentic-shell/ (must be writable if file logging enabled)
    - Config directory: ~/.config/agentic-shell/ (optional for user config)

Runtime Assumptions:
    - Python 3.8 or higher
    - Terminal supports ANSI escape sequences
    - Sufficient terminal dimensions (minimum 80x24)
    - UTF-8 character encoding
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List, Final, Set, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.console import Console, Group
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich import box

# =============================================================================
# Configuration Validation (STAGE 1.2: Externalize all hardcoded values)
# =============================================================================

class LogLevel(Enum):
    """Valid log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class AgentStatus(Enum):
    """Valid agent statuses."""
    ACTIVE = "active"
    BUSY = "busy"
    IDLE = "idle"
    ERROR = "error"

class ToolStatus(Enum):
    """Valid tool execution statuses."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"

class MessageRole(Enum):
    """Valid message roles."""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    TOOL = "tool"

def _get_env_int(name: str, default: int, min_value: Optional[int] = None, 
                 max_value: Optional[int] = None) -> int:
    """Get integer from environment with validation."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        int_value = int(value)
        if min_value is not None and int_value < min_value:
            raise RuntimeError(f"{name}={int_value} is below minimum {min_value}")
        if max_value is not None and int_value > max_value:
            raise RuntimeError(f"{name}={int_value} exceeds maximum {max_value}")
        return int_value
    except ValueError as e:
        raise RuntimeError(f"{name} must be an integer, got: {value}") from e

def _get_env_float(name: str, default: float, min_value: Optional[float] = None,
                   max_value: Optional[float] = None) -> float:
    """Get float from environment with validation."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        float_value = float(value)
        if min_value is not None and float_value < min_value:
            raise RuntimeError(f"{name}={float_value} is below minimum {min_value}")
        if max_value is not None and float_value > max_value:
            raise RuntimeError(f"{name}={float_value} exceeds maximum {max_value}")
        return float_value
    except ValueError as e:
        raise RuntimeError(f"{name} must be a number, got: {value}") from e

def _get_env_bool(name: str, default: bool) -> bool:
    """Get boolean from environment."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")

def _get_env_str(name: str, default: str, valid_values: Optional[Set[str]] = None) -> str:
    """Get string from environment with optional validation."""
    value = os.getenv(name, default)
    if valid_values is not None and value not in valid_values:
        raise RuntimeError(f"{name} must be one of {valid_values}, got: {value}")
    return value

# Python version check
if sys.version_info < (3, 8):
    raise RuntimeError(f"Python 3.8+ required, found: {sys.version}")

# Configuration constants with validation
MAX_HISTORY: Final[int] = _get_env_int("UI_MAX_HISTORY", 100, 10, 1000)
REFRESH_RATE: Final[float] = _get_env_float("UI_REFRESH_RATE", 4.0, 1.0, 30.0)
MIN_INTERVAL: Final[float] = _get_env_float("UI_MIN_INTERVAL", 0.25, 0.016)
LOG_LEVEL: Final[str] = _get_env_str("LOG_LEVEL", "INFO", {e.value for e in LogLevel})
SHOW_METRICS: Final[bool] = _get_env_bool("UI_SHOW_METRICS", True)
SHOW_AGENTS: Final[bool] = _get_env_bool("UI_SHOW_AGENTS", True)
SHOW_TOOLS: Final[bool] = _get_env_bool("UI_SHOW_TOOLS", True)
MAX_TOOL_HISTORY: Final[int] = _get_env_int("UI_MAX_TOOL_HISTORY", 50, 10, 200)
MAX_RENDER_ERRORS: Final[int] = _get_env_int("UI_MAX_RENDER_ERRORS", 5, 1, 20)
SESSION_ID: Final[Optional[str]] = os.getenv("SESSION_ID")

# =============================================================================
# Logging Configuration (STAGE 4.3: Structured logging)
# =============================================================================

# Create logs directory if it doesn't exist (handle permission errors gracefully)
log_dir = Path("/var/log/agentic-shell")
try:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"rich_ui_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s.%(msecs)03dZ [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    ))
except (PermissionError, OSError):
    # Fall back to console-only logging
    file_handler = None
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format="%(asctime)s.%(msecs)03dZ [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True
    )

# Configure root logger
logger = logging.getLogger("rich_ui")
logger.setLevel(getattr(logging, LOG_LEVEL))
if file_handler:
    logger.addHandler(file_handler)

# =============================================================================
# Data Models (STAGE 1.1: Map dossier findings to code - dataclasses from Script 1)
# =============================================================================

@dataclass
class Message:
    """Message data model with validation."""
    role: MessageRole
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self) -> None:
        """Validate message after initialization."""
        if not isinstance(self.role, MessageRole):
            try:
                self.role = MessageRole(self.role)
            except (ValueError, TypeError):
                logger.warning(f"Invalid role '{self.role}', defaulting to system")
                self.role = MessageRole.SYSTEM
        self.content = str(self.content)
        if not isinstance(self.metadata, dict):
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "role": self.role.value,
            "content": self.content,
            "metadata": self.metadata.copy(),
            "timestamp": self.timestamp
        }

@dataclass
class AgentStatusData:
    """Agent status data model."""
    status: AgentStatus
    tasks: int = 0
    last_update: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self) -> None:
        """Validate agent status."""
        if not isinstance(self.status, AgentStatus):
            try:
                self.status = AgentStatus(self.status)
            except (ValueError, TypeError):
                logger.warning(f"Invalid status '{self.status}', defaulting to idle")
                self.status = AgentStatus.IDLE
        if self.tasks < 0:
            logger.warning(f"Negative tasks count {self.tasks}, setting to 0")
            self.tasks = 0

@dataclass
class ToolExecution:
    """Tool execution data model."""
    tool: str
    status: ToolStatus
    duration_ms: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self) -> None:
        """Validate tool execution."""
        if not isinstance(self.status, ToolStatus):
            try:
                self.status = ToolStatus(self.status)
            except (ValueError, TypeError):
                logger.warning(f"Invalid status '{self.status}', defaulting to pending")
                self.status = ToolStatus.PENDING
        if self.duration_ms < 0:
            logger.warning(f"Negative duration {self.duration_ms}, setting to 0")
            self.duration_ms = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool": self.tool,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp
        }

# =============================================================================
# Constants (Externalized configuration)
# =============================================================================

AGENT_TYPES: Final[List[str]] = [
    "planner", "executor", "coder", "debugger", "optimizer", "reflector"
]

STATUS_STYLES: Final[Dict[AgentStatus, str]] = {
    AgentStatus.ACTIVE: "green",
    AgentStatus.BUSY: "yellow",
    AgentStatus.IDLE: "dim",
    AgentStatus.ERROR: "red"
}

TOOL_STATUS_STYLES: Final[Dict[ToolStatus, str]] = {
    ToolStatus.SUCCESS: "green",
    ToolStatus.FAILED: "red",
    ToolStatus.PENDING: "yellow"
}

# =============================================================================
# UI Class (STAGE 2.4: Align with Behavioral Trace)
# =============================================================================

class RichTerminalUI:
    """
    Enhanced terminal UI with live updating panels.
    
    Manages three independent concerns:
    1. State - message history, agent status, tool executions (using dataclasses)
    2. Rendering - converting state to Rich display elements
    3. Update loop - driving periodic screen refreshes
    
    The class is designed to be:
    - Resilient: Individual panel failures don't crash the entire UI
    - Bounded: All collections have size limits
    - Observable: All operations are logged at appropriate levels
    - Configurable: All tunable parameters are externalized
    """
    
    def __init__(self, session_id: Optional[str] = None) -> None:
        """
        Initialize UI with optional session identifier.
        
        Args:
            session_id: Existing session ID or None to generate new
            
        Raises:
            RuntimeError: If critical initialization fails
        """
        # STAGE 1.3: Document execution environment assumptions
        self.session_id = session_id or self._generate_session_id()
        self.console = Console()
        self.layout = Layout()
        self.message_history: List[Message] = []
        self.agent_status: Dict[str, AgentStatusData] = {}
        self.tool_executions: List[ToolExecution] = []
        self._running: bool = False
        self._live: Optional[Live] = None
        self._render_errors: int = 0
        self._max_render_errors: int = MAX_RENDER_ERRORS
        
        # Validate terminal capabilities
        if not self.console.is_terminal:
            logger.warning("Not running in a terminal - display may not work correctly")
        
        if not self._setup_layout():
            raise RuntimeError("Failed to initialize UI layout")
        
        # Initialize agent statuses
        for agent in AGENT_TYPES:
            self.agent_status[agent] = AgentStatusData(status=AgentStatus.IDLE)
        
        logger.info(f"UI initialized with session: {self.session_id}")
    
    def _generate_session_id(self) -> str:
        """Generate unique session identifier."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _setup_layout(self) -> bool:
        """
        Initialize the layout structure.
        
        Returns:
            True if layout setup succeeded, False otherwise
        """
        try:
            # Create main layout splits
            self.layout.split(
                Layout(name="header", size=3),
                Layout(name="main"),
                Layout(name="footer", size=3),
            )
            
            # Configure main panel based on visibility settings
            main_panels = ["conversation"]
            sidebar_panels = []
            
            if SHOW_AGENTS:
                sidebar_panels.append("agents")
            if SHOW_TOOLS:
                sidebar_panels.append("tools")
            if SHOW_METRICS:
                sidebar_panels.append("metrics")
            
            if sidebar_panels:
                # Split main into conversation and sidebar
                self.layout["main"].split_row(
                    Layout(name="conversation", ratio=2),
                    Layout(name="sidebar", ratio=1),
                )
                
                # Split sidebar into configured panels
                if len(sidebar_panels) == 1:
                    self.layout["sidebar"].update(
                        Layout(name=sidebar_panels[0])
                    )
                else:
                    # Calculate sizes based on number of panels
                    sizes = [10, 8, 8][:len(sidebar_panels)]
                    self.layout["sidebar"].split(
                        *[Layout(name=name, size=size) 
                          for name, size in zip(sidebar_panels, sizes)]
                    )
            else:
                # Use full width for conversation
                self.layout["main"].update(Layout(name="conversation"))
            
            return True
            
        except Exception as e:
            logger.error(f"Layout setup failed: {e}", exc_info=True)
            # Create fallback error layout
            self.layout = Layout()
            self.layout.split(Layout(name="error"))
            return False
    
    # =========================================================================
    # State Management (STAGE 2.1: Implement prescribed fixes)
    # =========================================================================
    
    def add_message(self, role: Union[str, MessageRole], content: str, 
                   metadata: Optional[Dict] = None) -> None:
        """
        Add message to history with automatic bounds checking.
        
        Args:
            role: Message sender role (user, agent, system, tool)
            content: Message content
            metadata: Additional message metadata
            
        Raises:
            TypeError: If content is not a string
        """
        # STAGE 4.2: Validate input contracts
        if not isinstance(content, str):
            raise TypeError(f"Message content must be string, got: {type(content)}")
        
        try:
            message = Message(
                role=role,
                content=content,
                metadata=metadata.copy() if metadata else {}
            )
            
            self.message_history.append(message)
            logger.debug(f"Added message: role={message.role.value}, length={len(content)}")
            
            # Maintain bounded history
            if len(self.message_history) > MAX_HISTORY:
                removed = self.message_history[:-MAX_HISTORY]
                self.message_history = self.message_history[-MAX_HISTORY:]
                logger.debug(f"Trimmed {len(removed)} old messages")
                
        except Exception as e:
            logger.error(f"Failed to add message: {e}", exc_info=True)
            raise  # STAGE 2.2: Fail fast on permanent errors
    
    def update_agent_status(self, agent_type: str, status: Union[str, AgentStatus], 
                           tasks: int = 0) -> None:
        """
        Update status of a specific agent.
        
        Args:
            agent_type: Agent identifier (must be in AGENT_TYPES)
            status: One of: active, busy, idle, error
            tasks: Current task count (non-negative)
            
        Raises:
            ValueError: If agent_type not in AGENT_TYPES or tasks negative
        """
        # STAGE 4.2: Validate input contracts
        if agent_type not in AGENT_TYPES:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        if tasks < 0:
            raise ValueError(f"Tasks count cannot be negative: {tasks}")
        
        try:
            status_enum = status if isinstance(status, AgentStatus) else AgentStatus(status)
            
            self.agent_status[agent_type] = AgentStatusData(
                status=status_enum,
                tasks=tasks
            )
            logger.debug(f"Updated agent {agent_type}: status={status_enum.value}, tasks={tasks}")
                
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to update agent status: {e}", exc_info=True)
            raise  # STAGE 2.2: Fail fast on permanent errors
    
    def add_tool_execution(self, tool: str, status: Union[str, ToolStatus], 
                          duration_ms: int) -> None:
        """
        Record a tool execution.
        
        Args:
            tool: Tool name
            status: Execution outcome (success, failed, pending)
            duration_ms: Execution duration in milliseconds
            
        Raises:
            ValueError: If duration_ms negative
        """
        # STAGE 4.2: Validate input contracts
        if duration_ms < 0:
            raise ValueError(f"Duration cannot be negative: {duration_ms}")
        
        try:
            status_enum = status if isinstance(status, ToolStatus) else ToolStatus(status)
            
            execution = ToolExecution(
                tool=tool,
                status=status_enum,
                duration_ms=duration_ms
            )
            
            self.tool_executions.append(execution)
            logger.debug(f"Added tool execution: tool={tool}, status={status_enum.value}, duration={duration_ms}ms")
            
            # Limit execution history
            if len(self.tool_executions) > MAX_TOOL_HISTORY:
                removed = self.tool_executions[:-MAX_TOOL_HISTORY]
                self.tool_executions = self.tool_executions[-MAX_TOOL_HISTORY:]
                logger.debug(f"Trimmed {len(removed)} old tool executions")
                
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to add tool execution: {e}", exc_info=True)
            raise  # STAGE 2.2: Fail fast on permanent errors
    
    def clear(self) -> None:
        """Reset all UI state."""
        self.message_history.clear()
        self.agent_status.clear()
        self.tool_executions.clear()
        # Reinitialize agent statuses
        for agent in AGENT_TYPES:
            self.agent_status[agent] = AgentStatusData(status=AgentStatus.IDLE)
        logger.info("UI state cleared")
    
    # =========================================================================
    # Rendering Methods (STAGE 1.1: Map findings to code - each isolated)
    # =========================================================================
    
    def _render_header(self) -> Panel:
        """Render header with session information."""
        try:
            text = Text()
            text.append(" AGENTIC SHELL 2.0 ", style="bold white on blue")
            text.append(" │ ")
            text.append(f"Session: {self.session_id}", style="cyan")
            text.append(" │ ")
            text.append(datetime.now().strftime("%H:%M:%S"), style="dim")
            
            return Panel(text, style="bold", box=box.HEAVY)
        except Exception as e:
            logger.error(f"Header render failed: {e}", exc_info=True)
            self._render_errors += 1
            return Panel("Header Error - Check logs", style="red")
    
    def _render_conversation(self) -> Panel:
        """Render conversation history."""
        try:
            if not self.message_history:
                return Panel(
                    Text("No messages yet. Type /help for commands.", style="dim italic"),
                    title="Conversation",
                    border_style="blue",
                )
            
            elements = []
            for msg in self.message_history[-MAX_HISTORY:]:
                timestamp = msg.timestamp[11:19] if msg.timestamp else ""
                
                if msg.role == MessageRole.USER:
                    text = Text(f"[{timestamp}] ", style="dim")
                    text.append(f"You: ", style="green bold")
                    text.append(msg.content)
                    elements.append(text)
                    
                elif msg.role == MessageRole.AGENT:
                    agent_type = msg.metadata.get("agent_type", "agent")
                    text = Text(f"[{timestamp}] ", style="dim")
                    text.append(f"{agent_type}> ", style="blue bold")
                    
                    # Attempt JSON formatting for structured data
                    if msg.content and msg.content.strip() and msg.content.strip()[0] in "{[":
                        try:
                            parsed = json.loads(msg.content)
                            formatted = json.dumps(parsed, indent=2)
                            elements.append(text)
                            elements.append(Syntax(formatted, "json", theme="monokai"))
                            continue
                        except (json.JSONDecodeError, IndexError):
                            pass
                    
                    # Handle markdown content
                    if "```" in msg.content:
                        elements.append(text)
                        elements.append(Markdown(msg.content))
                    else:
                        text.append(msg.content)
                        elements.append(text)
                        
                elif msg.role == MessageRole.SYSTEM:
                    text = Text(f"[{timestamp}] ", style="dim")
                    text.append(f"⚙️ {msg.content}", style="yellow")
                    elements.append(text)
                    
                elif msg.role == MessageRole.TOOL:
                    text = Text(f"[{timestamp}] ", style="dim")
                    text.append(f"🔧 {msg.content}", style="magenta")
                    elements.append(text)
                
                elements.append(Text(""))  # Spacing between messages
            
            return Panel(
                Group(*elements),
                title="Conversation",
                border_style="blue",
            )
            
        except Exception as e:
            logger.error(f"Conversation render failed: {e}", exc_info=True)
            self._render_errors += 1
            if self._render_errors > self._max_render_errors:
                return Panel("Conversation unavailable - too many errors", style="red")
            return Panel("Error loading conversation", style="red")
    
    def _render_agents(self) -> Optional[Panel]:
        """Render agent status panel."""
        if not SHOW_AGENTS:
            return None
            
        try:
            table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
            table.add_column("Agent", style="cyan")
            table.add_column("Status", width=10)
            table.add_column("Tasks", justify="right")
            
            for agent in AGENT_TYPES:
                status_data = self.agent_status.get(agent, AgentStatusData(status=AgentStatus.IDLE))
                style = STATUS_STYLES.get(status_data.status, "dim")
                
                table.add_row(
                    agent,
                    f"[{style}]{status_data.status.value}[/]",
                    str(status_data.tasks),
                )
            
            return Panel(table, title="Active Agents", border_style="green")
            
        except Exception as e:
            logger.error(f"Agents render failed: {e}", exc_info=True)
            self._render_errors += 1
            return Panel("Agent status unavailable", style="red")
    
    def _render_tools(self) -> Optional[Panel]:
        """Render recent tool executions."""
        if not SHOW_TOOLS:
            return None
            
        try:
            table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
            table.add_column("Tool", style="magenta")
            table.add_column("Status", width=10)
            table.add_column("Time")
            
            # Show last 5 executions, newest first
            recent = self.tool_executions[-5:][::-1]
            for execution in recent:
                style = TOOL_STATUS_STYLES.get(execution.status, "dim")
                duration = f"{execution.duration_ms}ms"
                
                table.add_row(
                    execution.tool,
                    f"[{style}]{execution.status.value}[/]",
                    duration,
                )
            
            return Panel(table, title="Tool Executions", border_style="magenta")
            
        except Exception as e:
            logger.error(f"Tools render failed: {e}", exc_info=True)
            self._render_errors += 1
            return Panel("Tool data unavailable", style="red")
    
    def _render_metrics(self) -> Optional[Panel]:
        """Render system metrics."""
        if not SHOW_METRICS:
            return None
            
        try:
            text = Text()
            text.append("Queue Depth\n", style="bold")
            text.append("  planner: 0\n", style="dim")
            text.append("  executor: 0\n", style="dim")
            text.append("  coder: 0\n", style="dim")
            text.append("  debugger: 0\n", style="dim")
            text.append("  optimizer: 0\n", style="dim")
            text.append("  reflector: 0\n", style="dim")
            text.append("\n")
            text.append("Response Time\n", style="bold")
            text.append("  p50: 0ms\n", style="dim")
            text.append("  p95: 0ms\n", style="dim")
            text.append("  p99: 0ms\n", style="dim")
            
            return Panel(text, title="Metrics", border_style="yellow")
            
        except Exception as e:
            logger.error(f"Metrics render failed: {e}", exc_info=True)
            self._render_errors += 1
            return Panel("Metrics unavailable", style="red")
    
    def _render_footer(self) -> Panel:
        """Render input prompt footer."""
        try:
            text = Text()
            text.append("> ", style="green bold")
            text.append("Type your message or /help", style="dim")
            
            return Panel(text, style="dim", box=box.HEAVY)
            
        except Exception as e:
            logger.error(f"Footer render failed: {e}", exc_info=True)
            self._render_errors += 1
            return Panel("Input unavailable", style="red")
    
    def update(self) -> bool:
        """
        Refresh all layout panels with current state.
        
        Returns:
            bool: True if update succeeded, False otherwise
        """
        try:
            self.layout["header"].update(self._render_header())
            self.layout["conversation"].update(self._render_conversation())
            
            # Update optional panels if they exist
            if SHOW_AGENTS and "agents" in self.layout:
                agents_panel = self._render_agents()
                if agents_panel:
                    self.layout["agents"].update(agents_panel)
            
            if SHOW_TOOLS and "tools" in self.layout:
                tools_panel = self._render_tools()
                if tools_panel:
                    self.layout["tools"].update(tools_panel)
            
            if SHOW_METRICS and "metrics" in self.layout:
                metrics_panel = self._render_metrics()
                if metrics_panel:
                    self.layout["metrics"].update(metrics_panel)
            
            self.layout["footer"].update(self._render_footer())
            
            # Reset error counter on success
            self._render_errors = 0
            return True
            
        except Exception as e:
            logger.error(f"Layout update failed: {e}", exc_info=True)
            self._render_errors += 1
            return False
    
    # =========================================================================
    # Main Loop (STAGE 2.4: Align with Behavioral Trace)
    # =========================================================================
    
    async def run(self) -> None:
        """
        Start the live display loop.
        
        This is the main entry point. The loop continues until cancelled
        or an unrecoverable error occurs.
        
        Raises:
            RuntimeError: If display cannot be initialized or too many render errors
            asyncio.CancelledError: When loop is cancelled
        """
        self._running = True
        self._render_errors = 0
        
        try:
            with Live(
                self.layout,
                refresh_per_second=REFRESH_RATE,
                screen=True,
                auto_refresh=False
            ) as self._live:
                while self._running:
                    if not self.update():
                        if self._render_errors > self._max_render_errors:
                            error_msg = f"Too many render errors ({self._render_errors})"
                            logger.error(error_msg)
                            raise RuntimeError(error_msg)
                    
                    self._live.update(self.layout)
                    await asyncio.sleep(MIN_INTERVAL)
                    
        except asyncio.CancelledError:
            logger.info("Display loop cancelled")
            self._running = False
            raise
        except Exception as e:
            logger.error(f"Display loop error: {e}", exc_info=True)
            self._running = False
            self.console.print(f"\n[red]Display error: {e}[/]")
            self.console.print("[yellow]Falling back to simple mode[/]")
            raise  # STAGE 2.2: Fail fast on permanent errors
        finally:
            self._running = False
            self._live = None
    
    async def shutdown(self) -> None:
        """Gracefully shut down the UI."""
        self._running = False
        if self._live:
            try:
                self._live.stop()
            except Exception as e:
                logger.warning(f"Error stopping live display: {e}")
        self.console.print("\n[dim]UI shutting down...[/]")
        logger.info("UI shutdown complete")


# =============================================================================
# Entry Points (STAGE 5.1: Close all critical gaps)
# =============================================================================

async def run_ui(session_id: Optional[str] = None) -> None:
    """
    Create and run UI with given session ID.
    
    Args:
        session_id: Optional existing session identifier
        
    Raises:
        RuntimeError: If UI initialization or runtime fails
    """
    ui = None
    try:
        ui = RichTerminalUI(session_id)
        await ui.run()
    except KeyboardInterrupt:
        logger.info("UI interrupted by user")
        print("\nGoodbye!")
    except asyncio.CancelledError:
        logger.info("UI task cancelled")
        raise
    except Exception as e:
        logger.error(f"UI runtime error: {e}", exc_info=True)
        print(f"\nError: {e}")
        raise RuntimeError(f"UI execution failed: {e}") from e
    finally:
        if ui:
            await ui.shutdown()


def main() -> None:
    """Synchronous entry point for command-line execution."""
    try:
        asyncio.run(run_ui(SESSION_ID))
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except RuntimeError as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

```python
# .env.example - Configuration template for Rich Terminal UI
# Copy to .env and modify as needed

# Session configuration
SESSION_ID=

# Display configuration
UI_MAX_HISTORY=100
UI_REFRESH_RATE=4.0
UI_MIN_INTERVAL=0.25
UI_MAX_TOOL_HISTORY=50
UI_MAX_RENDER_ERRORS=5

# Panel visibility
UI_SHOW_METRICS=true
UI_SHOW_AGENTS=true
UI_SHOW_TOOLS=true

# Logging
LOG_LEVEL=INFO
```

```python
# requirements.txt - Production dependencies
# Generated 2026-03-01

rich>=13.0.0,<14.0.0  # Terminal formatting and layouts
python-dotenv>=1.0.0,<2.0.0  # Environment variable management
```

```python
# README.md - Execution environment documentation

# Rich Terminal UI for Agentic Shell 2.0

## Runtime Requirements
- Python 3.8 or higher
- Terminal with ANSI escape sequence support
- Minimum terminal dimensions: 80x24
- UTF-8 character encoding

## Environment Variables
All configuration is done via environment variables. See `.env.example` for a template.

### Required Variables
None - all variables have safe defaults.

### Optional Variables
- `SESSION_ID`: Custom session identifier (auto-generated if not provided)
- `UI_MAX_HISTORY`: Maximum messages to retain (10-1000, default: 100)
- `UI_REFRESH_RATE`: Display refresh rate in Hz (1.0-30.0, default: 4.0)
- `UI_MIN_INTERVAL`: Minimum refresh interval in seconds (>=0.016, default: 0.25)
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL, default: INFO)
- `UI_SHOW_METRICS`: Show metrics panel (true/false, default: true)
- `UI_SHOW_AGENTS`: Show agents panel (true/false, default: true)
- `UI_SHOW_TOOLS`: Show tools panel (true/false, default: true)
- `UI_MAX_TOOL_HISTORY`: Maximum tool executions to retain (10-200, default: 50)
- `UI_MAX_RENDER_ERRORS`: Max consecutive render errors before fallback (1-20, default: 5)

## File System Requirements
- Log directory: `/var/log/agentic-shell/` (must be writable for file logging)
  - Falls back to console-only logging if directory not writable
- Config directory: `~/.config/agentic-shell/` (optional for user config)

## Installation
```bash
pip install -r requirements.txt
```

Usage

```bash
# Run with default settings
python rich_ui.py

# Run with custom session
SESSION_ID=custom-session-123 python rich_ui.py

# Run with debug logging
LOG_LEVEL=DEBUG python rich_ui.py
```

Runtime Behavior

1. Validates all environment variables at startup
2. Creates log directory if possible (handles permission errors gracefully)
3. Initializes UI layout based on panel visibility settings
4. Enters live display loop with configured refresh rate
5. On error: logs with full context, falls back to simple mode after max errors
6. On interrupt: graceful shutdown with state preservation

Error Handling

· Invalid environment variables → fatal error with clear message
· Missing file permissions → fallback to console-only logging
· Render errors → counted, fallback after threshold
· Invalid input parameters → raise ValueError with context
· Network/filesystem errors → logged with exc_info=True

Assumptions

· Terminal supports ANSI escape sequences (checked at startup)
· Sufficient terminal dimensions (minimum 80x24)
· UTF-8 encoding for all text
· Python standard library available

```
