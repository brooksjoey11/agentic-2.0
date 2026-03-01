"""Rich terminal UI helpers."""
from rich.console import Console
from rich.table import Table

console = Console()


def print_table(title: str, rows: list[dict], columns: list[str] | None = None) -> None:
    """Render a list of dicts as a Rich table."""
    if not rows:
        console.print(f"[yellow]No {title.lower()} found.[/yellow]")
        return
    cols = columns or list(rows[0].keys())
    table = Table(title=title, show_header=True, header_style="bold cyan")
    for col in cols:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(row.get(c, "")) for c in cols])
    console.print(table)
