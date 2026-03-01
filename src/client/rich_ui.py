"""
Rich UI Components for Agentic Shell Client
Provides enhanced terminal UI with panels, layouts, and real-time updates
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.console import Console, Group
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.columns import Columns
from rich import box
import asyncio


class RichTerminalUI:
    """
    Enhanced terminal UI with live updating panels
    """
    
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.setup_layout()
        self.message_history: List[Dict[str, Any]] = []
        self.agent_status: Dict[str, str] = {}
        self.tool_executions: List[Dict[str, Any]] = []
        
    def setup_layout(self):
        """Initialize the layout structure"""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )
        
        self.layout["main"].split_row(
            Layout(name="conversation", ratio=2),
            Layout(name="sidebar", ratio=1),
        )
        
        self.layout["sidebar"].split(
            Layout(name="agents", size=10),
            Layout(name="tools", size=8),
            Layout(name="metrics", size=8),
        )
        
    def render_header(self) -> Panel:
        """Render the header panel"""
        text = Text()
        text.append(" AGENTIC SHELL 2.0 ", style="bold white on blue")
        text.append(" │ ")
        text.append(f"Session: {self.session_id}", style="cyan")
        text.append(" │ ")
        text.append(datetime.now().strftime("%H:%M:%S"), style="dim")
        
        return Panel(text, style="bold", box=box.HEAVY)
    
    def render_conversation(self) -> Panel:
        """Render the conversation panel with message history"""
        elements = []
        
        for msg in self.message_history[-20:]:  # Show last 20 messages
            timestamp = msg.get("timestamp", "")[11:19] if msg.get("timestamp") else ""
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            if role == "user":
                text = Text(f"[{timestamp}] ", style="dim")
                text.append(f"You: ", style="green bold")
                text.append(content)
                elements.append(text)
            elif role == "agent":
                agent_type = msg.get("metadata", {}).get("agent_type", "agent")
                text = Text(f"[{timestamp}] ", style="dim")
                text.append(f"{agent_type}> ", style="blue bold")
                
                # Format based on content type
                if content.strip().startswith(("{", "[")):
                    try:
                        # Pretty print JSON
                        import json
                        parsed = json.loads(content)
                        formatted = json.dumps(parsed, indent=2)
                        elements.append(text)
                        elements.append(Syntax(formatted, "json", theme="monokai"))
                        continue
                    except:
                        pass
                
                if "```" in content:
                    # Contains code blocks
                    elements.append(text)
                    elements.append(Markdown(content))
                else:
                    text.append(content)
                    elements.append(text)
            elif role == "system":
                text = Text(f"[{timestamp}] ", style="dim")
                text.append(f"⚙️ {content}", style="yellow")
                elements.append(text)
            elif role == "tool":
                text = Text(f"[{timestamp}] ", style="dim")
                text.append(f"🔧 {content}", style="magenta")
                elements.append(text)
            
            elements.append(Text(""))  # Spacing
        
        if not elements:
            elements = [Text("No messages yet. Type /help for commands.", style="dim italic")]
        
        return Panel(
            Group(*elements) if len(elements) > 1 else elements[0],
            title="Conversation",
            border_style="blue",
        )
    
    def render_agents(self) -> Panel:
        """Render agent status panel"""
        table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
        table.add_column("Agent", style="cyan")
        table.add_column("Status", width=10)
        table.add_column("Tasks", justify="right")
        
        agents = ["planner", "executor", "coder", "debugger", "optimizer", "reflector"]
        
        for agent in agents:
            status = self.agent_status.get(agent, "idle")
            status_style = {
                "active": "green",
                "busy": "yellow",
                "idle": "dim",
                "error": "red",
            }.get(status, "dim")
            
            tasks = self.agent_status.get(f"{agent}_tasks", "0")
            
            table.add_row(
                agent,
                f"[{status_style}]{status}[/]",
                tasks,
            )
        
        return Panel(table, title="Active Agents", border_style="green")
    
    def render_tools(self) -> Panel:
        """Render recent tool executions"""
        table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
        table.add_column("Tool", style="magenta")
        table.add_column("Status", width=10)
        table.add_column("Time")
        
        for exec in self.tool_executions[-5:]:  # Last 5 executions
            tool = exec.get("tool", "unknown")
            status = exec.get("status", "unknown")
            status_style = "green" if status == "success" else "red" if status == "failed" else "yellow"
            duration = f"{exec.get('duration_ms', 0)}ms"
            
            table.add_row(
                tool,
                f"[{status_style}]{status}[/]",
                duration,
            )
        
        return Panel(table, title="Tool Executions", border_style="magenta")
    
    def render_metrics(self) -> Panel:
        """Render system metrics"""
        # This would be populated from the orchestrator
        text = Text()
        text.append("Queue Depth\n", style="bold")
        text.append("  planner: 3\n", style="dim")
        text.append("  executor: 7\n", style="dim")
        text.append("  coder: 2\n", style="dim")
        text.append("  debugger: 1\n", style="dim")
        text.append("  optimizer: 0\n", style="dim")
        text.append("  reflector: 0\n", style="dim")
        text.append("\n")
        text.append("Response Time\n", style="bold")
        text.append("  p50: 234ms\n", style="dim")
        text.append("  p95: 567ms\n", style="dim")
        text.append("  p99: 890ms\n", style="dim")
        
        return Panel(text, title="Metrics", border_style="yellow")
    
    def render_footer(self) -> Panel:
        """Render the footer with input prompt"""
        text = Text()
        text.append("> ", style="green bold")
        text.append("Type your message or /help", style="dim")
        
        return Panel(text, style="dim", box=box.HEAVY)
    
    def update(self):
        """Update the entire layout"""
        self.layout["header"].update(self.render_header())
        self.layout["conversation"].update(self.render_conversation())
        self.layout["agents"].update(self.render_agents())
        self.layout["tools"].update(self.render_tools())
        self.layout["metrics"].update(self.render_metrics())
        self.layout["footer"].update(self.render_footer())
    
    async def live_display(self):
        """Run the live display"""
        with Live(self.layout, refresh_per_second=4, screen=True) as live:
            while True:
                self.update()
                live.update(self.layout)
                await asyncio.sleep(0.25)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to history"""
        self.message_history.append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        })
    
    def update_agent_status(self, agent_type: str, status: str, tasks: int = 0):
        """Update agent status"""
        self.agent_status[agent_type] = status
        if tasks:
            self.agent_status[f"{agent_type}_tasks"] = str(tasks)
    
    def add_tool_execution(self, tool: str, status: str, duration_ms: int):
        """Add a tool execution record"""
        self.tool_executions.append({
            "tool": tool,
            "status": status,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
        })
    
    def clear(self):
        """Clear all state"""
        self.message_history = []
        self.agent_status = {}
        self.tool_executions = []
