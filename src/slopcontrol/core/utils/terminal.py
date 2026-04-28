import os
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


def get_project_dir(project_dir: Optional[str] = None) -> Path:
    """Get the project directory, defaulting to SLOPCONTROL_PROJECT_DIR or ./projects."""
    if project_dir:
        return Path(project_dir)

    env_dir = os.environ.get("SLOPCONTROL_PROJECT_DIR")
    if env_dir:
        return Path(env_dir)

    return Path("./projects")


def ensure_project_dir(project_dir: Optional[str] = None) -> Path:
    """Ensure project directory exists and return path."""
    dir_path = get_project_dir(project_dir)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def display_markdown(text: str) -> None:
    """Display markdown-formatted text in terminal."""
    console.print(text, markup=True)


def display_success(message: str) -> None:
    """Display success message."""
    console.print(f"[green]✓[/green] {message}")


def display_error(message: str) -> None:
    """Display error message."""
    console.print(f"[red]✗[/red] {message}")


def display_warning(message: str) -> None:
    """Display warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def display_info(message: str) -> None:
    """Display info message."""
    console.print(f"[blue]ℹ[/blue] {message}")
