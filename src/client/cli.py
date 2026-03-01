#!/usr/bin/env python3
"""
Agentic Shell 2.0 - CLI Client
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
import argparse
import signal

import websockets
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box
import readline
import atexit

console = Console()

class AgenticShellClient:
    """Rich CLI client for Agentic Shell"""
    
    def __init__(self, server: str = "ws://localhost:8000/ws", session_id: Optional[str] = None):
        self.server = server
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.ws = None
        self.history = []
        self.running = True
        
        # Setup readline for command history
        self.history_file = os.path.expanduser("~/.agentic_shell_history")
        try:
            readline.read_history_file(self.history_file)
        except FileNotFoundError:
            pass
        atexit.register(readline.write_history_file, self.history_file)
        
    async def connect(self):
        """Connect to orchestrator"""
        try:
            self.ws = await websockets.connect(f"{self.server}/{self.session_id}")
            console.print(f"[bold green]✅ Connected[/] to [cyan]{self.server}[/]")
            console.print(f"[bold]Session ID:[/] [yellow]{self.session_id}[/]")
            
            # Receive welcome message
            welcome = await self.ws.recv()
            data = json.loads(welcome)
            console.print(Panel(data["content"], title="Welcome", border_style="blue"))
            
        except Exception as e:
            console.print(f"[bold red]❌ Connection failed:[/] {e}")
            sys.exit(1)
    
    async def send_message(self, content: str, role: str = "user") -> None:
        """Send message to orchestrator"""
        message = {
            "role": role,
            "content": content,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "client": "rich-cli"
            }
        }
        await self.ws.send(json.dumps(message))
        self.history.append({"role": "user", "content": content})
    
    async def receive_response(self) -> Dict[str, Any]:
        """Receive response from orchestrator"""
        response = await self.ws.recv()
        data = json.loads(response)
        self.history.append({"role": "agent", "content": data.get("message", {}).get("content", "")})
        return data
    
    async def handle_command(self, cmd: str) -> bool:
        """Handle special commands"""
        cmd = cmd.lower().strip()
        
        if cmd == "/exit" or cmd == "/quit":
            console.print("[yellow]Goodbye![/]")
            return False
            
        elif cmd == "/help":
            self.show_help()
            
        elif cmd == "/history":
            self.show_history()
            
        elif cmd == "/clear":
            os.system('clear' if os.name == 'posix' else 'cls')
            
        elif cmd == "/session":
            console.print(f"[bold]Session ID:[/] [cyan]{self.session_id}[/]")
            
        elif cmd.startswith("/save "):
            filename = cmd[6:]
            self.save_session(filename)
            
        elif cmd.startswith("/load "):
            filename = cmd[6:]
            self.load_session(filename)
            
        elif cmd == "/stats":
            await self.show_stats()
            
        elif cmd == "/tools":
            await self.list_tools()
            
        else:
            # Not a command
            return True
            
        return True
    
    def show_help(self):
        """Show help panel"""
        table = Table(title="Agentic Shell Commands", box=box.ROUNDED)
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description")
        
        table.add_row("/help", "Show this help")
        table.add_row("/exit", "Exit the shell")
        table.add_row("/history", "Show conversation history")
        table.add_row("/clear", "Clear the screen")
        table.add_row("/session", "Show current session ID")
        table.add_row("/save <file>", "Save session to file")
        table.add_row("/load <file>", "Load session from file")
        table.add_row("/stats", "Show system statistics")
        table.add_row("/tools", "List available tools")
        
        console.print(table)
    
    def show_history(self):
        """Show conversation history"""
        if not self.history:
            console.print("[yellow]No history[/]")
            return
            
        table = Table(box=box.SIMPLE)
        table.add_column("#", style="dim", width=3)
        table.add_column("Role", style="bold", width=8)
        table.add_column("Content", width=70)
        
        for i, entry in enumerate(self.history[-20:], 1):
            role = entry["role"]
            content = entry["content"][:60] + "..." if len(entry["content"]) > 60 else entry["content"]
            role_style = "green" if role == "user" else "blue"
            table.add_row(str(i), f"[{role_style}]{role}[/]", content)
            
        console.print(table)
    
    def save_session(self, filename: str):
        """Save session to file"""
        try:
            with open(filename, 'w') as f:
                json.dump({
                    "session_id": self.session_id,
                    "history": self.history
                }, f, indent=2)
            console.print(f"[green]✅ Session saved to {filename}[/]")
        except Exception as e:
            console.print(f"[red]❌ Save failed: {e}[/]")
    
    def load_session(self, filename: str):
        """Load session from file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            self.session_id = data.get("session_id", self.session_id)
            self.history = data.get("history", [])
            console.print(f"[green]✅ Session loaded from {filename}[/]")
        except Exception as e:
            console.print(f"[red]❌ Load failed: {e}[/]")
    
    async def show_stats(self):
        """Show system statistics"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8000/stats") as resp:
                    if resp.status == 200:
                        stats = await resp.json()
                        
                        table = Table(title="System Statistics", box=box.ROUNDED)
                        table.add_column("Metric", style="cyan")
                        table.add_column("Value")
                        
                        table.add_row("Total Messages", str(stats.get("total_messages", 0)))
                        table.add_row("Active Sessions", str(stats.get("active_sessions", 0)))
                        table.add_row("Tool Executions", str(stats.get("tool_executions", 0)))
                        
                        console.print(table)
                    else:
                        console.print("[yellow]Stats not available[/]")
        except:
            console.print("[yellow]Could not fetch stats[/]")
    
    async def list_tools(self):
        """List available tools"""
        table = Table(title="Available Tools", box=box.ROUNDED)
        table.add_column("Tool", style="cyan")
        table.add_column("Description")
        
        table.add_row("shell", "Execute shell commands")
        table.add_row("kubernetes", "Manage Kubernetes clusters")
        table.add_row("docker", "Manage Docker containers")
        table.add_row("aws", "AWS cloud services")
        table.add_row("github", "GitHub operations")
        
        console.print(table)
    
    def format_response(self, content: str) -> str:
        """Format response for display"""
        # Try to parse as JSON
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "stdout" in data:
                # Tool execution result
                result = []
                if data.get("stdout"):
                    result.append(Syntax(data["stdout"], "bash", theme="monokai"))
                if data.get("stderr"):
                    result.append(Panel(data["stderr"], title="Error", border_style="red"))
                return result
        except:
            pass
        
        # Check if it looks like markdown
        if any(marker in content for marker in ['#', '`', '*', '- [ ]', '|']):
            return Markdown(content)
        
        # Check if it looks like code
        if 'def ' in content or 'class ' in content or 'import ' in content or 'function' in content:
            return Syntax(content, "python", theme="monokai")
        
        return content
    
    async def interactive_session(self):
        """Main interactive loop"""
        await self.connect()
        
        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
        
        console.print("\n[dim]Type /help for commands[/]\n")
        
        while self.running:
            try:
                # Get user input
                user_input = Prompt.ask("[bold green]You[/]")
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith("/"):
                    if not await self.handle_command(user_input):
                        break
                    continue
                
                # Send to orchestrator
                await self.send_message(user_input)
                
                # Show thinking indicator
                with console.status("[bold green]Agents thinking..."):
                    response = await self.receive_response()
                
                # Display response
                message = response.get("message", {})
                content = message.get("content", "")
                agent_type = message.get("metadata", {}).get("agent_type", "agent")
                
                console.print(f"\n[bold blue]{agent_type}>[/]")
                
                formatted = self.format_response(content)
                if isinstance(formatted, list):
                    for item in formatted:
                        console.print(item)
                else:
                    console.print(formatted)
                
                console.print()  # Empty line
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted[/]")
                break
            except websockets.exceptions.ConnectionClosed:
                console.print("[red]Connection lost[/]")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")
    
    async def shutdown(self):
        """Graceful shutdown"""
        self.running = False
        if self.ws:
            await self.ws.close()
        console.print("\n[yellow]Shutting down...[/]")

def main():
    parser = argparse.ArgumentParser(description="Agentic Shell 2.0 Client")
    parser.add_argument("--server", default="ws://localhost:8000/ws", help="WebSocket server URL")
    parser.add_argument("--session", help="Session ID")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    client = AgenticShellClient(server=args.server, session_id=args.session)
    
    try:
        asyncio.run(client.interactive_session())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/]")

if __name__ == "__main__":
    main()