"""Command-line interface for agentic-shell."""
import typer
import httpx
from rich.console import Console

app = typer.Typer(help="agentic-shell CLI")
console = Console()

BASE_URL = "http://localhost:8000"


@app.command()
def health() -> None:
    """Check orchestrator health."""
    response = httpx.get(f"{BASE_URL}/health/")
    console.print(response.json())


@app.command()
def list_agents() -> None:
    """List all registered agents."""
    response = httpx.get(f"{BASE_URL}/agents/")
    console.print_json(response.text)


@app.command()
def list_tools() -> None:
    """List all registered tools."""
    response = httpx.get(f"{BASE_URL}/tools/")
    console.print_json(response.text)


if __name__ == "__main__":
    app()
