"""Terminal utilities for the SlopControl CLI."""

from rich.console import Console

console = Console()


def get_terminal_size() -> tuple[int, int]:
    """Get terminal width and height."""
    return console.size


def print_step(step: int, total: int, message: str) -> None:
    """Print a step indicator.

    Args:
        step: Current step number
        total: Total number of steps
        message: Step description
    """
    console.print(f"\n[bold cyan]Step {step}/{total}:[/bold cyan] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[blue]ℹ[/blue] {message}")
