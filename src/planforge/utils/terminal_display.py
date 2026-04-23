"""Terminal display utilities for rendering images in the terminal."""

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn


console = Console()


def get_terminal_size() -> tuple[int, int]:
    """Get terminal width and height."""
    return console.size


def calculate_image_size(
    img_width: int,
    img_height: int,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None,
) -> tuple[int, int]:
    """Calculate scaled image size for terminal display.

    Args:
        img_width: Original image width
        img_height: Original image height
        max_width: Maximum width (default: terminal width - 10)
        max_height: Maximum height (default: 40)

    Returns:
        Tuple of (new_width, new_height)
    """
    terminal_width, terminal_height = get_terminal_size()

    if max_width is None:
        max_width = max(terminal_width - 10, 40)
    if max_height is None:
        max_height = min(terminal_height // 2, 40)

    width_ratio = img_width / max_width if img_width > max_width else 1
    height_ratio = img_height / max_height if img_height > max_height else 1

    ratio = max(width_ratio, height_ratio)

    if ratio > 1:
        new_width = int(img_width / ratio)
        new_height = int(img_height / ratio)
        return new_width, new_height

    return img_width, img_height


def display_image_ascii(
    img_path: str,
    max_height: int = 30,
    use_color: bool = True,
) -> str:
    """Convert image to ASCII art representation.

    Args:
        img_path: Path to the image file
        max_height: Maximum height in characters
        use_color: Use colored ASCII characters

    Returns:
        ASCII art representation
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return f"[Image available at: {img_path}]"

    img = Image.open(img_path)

    terminal_width, _ = get_terminal_size()
    max_width = min(terminal_width - 10, 120)

    aspect_ratio = img.height / img.width
    new_width = max_width
    new_height = int(max_width * aspect_ratio)

    if new_height > max_height:
        new_height = max_height
        new_width = int(max_height / aspect_ratio)

    img = img.resize((new_width, new_height))

    if use_color:
        img_rgb = img.convert("RGB")
        img_array = np.array(img_rgb)

        ascii_lines = []
        for row in img_array:
            line = ""
            for pixel in row:
                r, g, b = pixel
                brightness = int(0.299 * r + 0.587 * g + 0.114 * b)
                chars = " .:-=+*#%@"
                index = min(int(brightness / 255 * (len(chars) - 1)), len(chars) - 1)
                line += chars[index]
            ascii_lines.append(line)
    else:
        img_array = np.array(img.convert("L"))
        chars = " .:-=+*#%@"
        scale = 255 / len(chars)

        ascii_lines = []
        for row in img_array:
            line = ""
            for pixel in row:
                index = min(int(pixel / scale), len(chars) - 1)
                line += chars[index]
            ascii_lines.append(line)

    return "\n".join(ascii_lines)


def display_preview_panel(
    image_path: str,
    title: str = "Preview",
    max_height: int = 30,
    style: str = "cyan",
) -> None:
    """Display a preview image in a Rich panel.

    Args:
        image_path: Path to the preview image
        title: Title for the panel
        max_height: Maximum height for ASCII display
        style: Border style color
    """
    img_path = Path(image_path)

    if not img_path.exists():
        console.print(f"[red]Image not found: {image_path}[/red]")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Rendering preview...", total=None)
        ascii_art = display_image_ascii(str(img_path), max_height=max_height)

    panel = Panel(
        ascii_art,
        title=title,
        border_style=style,
        padding=(1, 1),
    )
    console.print(panel)


def display_multiview_previews(
    image_paths: dict[str, str],
    title: str = "Multi-View Preview",
    layout: str = "horizontal",
) -> None:
    """Display multiple preview images.

    Args:
        image_paths: Dict of view name to image path
        title: Title for the display
        layout: 'horizontal' or 'vertical' layout
    """
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("View", style="cyan", width=15)

    views_data = {}
    for view_name, img_path in image_paths.items():
        if Path(img_path).exists():
            views_data[view_name] = display_image_ascii(img_path, max_height=18)

    if not views_data:
        console.print("[yellow]No preview images available[/yellow]")
        return

    if layout == "horizontal":
        table.add_column("Preview", style="white", width=55)
        for view_name, ascii in views_data.items():
            table.add_row(view_name, ascii)
    else:
        for view_name, ascii in views_data.items():
            table.add_row(f"[bold]{view_name}[/bold]", ascii)
            console.print(table)
            table = Table(border_style="cyan", show_header=False)
            table.add_column(width=70)

    console.print(table)


def display_model_info_table(info: dict, title: str = "Model Information") -> None:
    """Display model information in a formatted table.

    Args:
        info: Model information dictionary
        title: Table title
    """
    table = Table(title=title, show_header=False, border_style="cyan")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="white", width=25)
    table.add_column("Unit", style="dim", width=10)

    for key, value in info.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, float):
                    table.add_row(sub_key, f"{sub_value:.2f}", "mm")
                else:
                    table.add_row(sub_key, str(sub_value), "")
        else:
            if isinstance(value, float):
                table.add_row(key, f"{value:.2f}", "mm" if "volume" not in key else "mm³")
            else:
                table.add_row(key, str(value), "")

    console.print(table)


def display_design_history_entry(
    version: int,
    commit_hash: str,
    message: str,
    timestamp: str,
    author: str = "PlanForge",
    changes: Optional[dict] = None,
) -> None:
    """Display a design history entry in a formatted panel.

    Args:
        version: Version number
        commit_hash: Git commit hash
        message: Commit message
        timestamp: Timestamp string
        author: Commit author
        changes: Optional dict of changes
    """
    content_lines = [
        f"[cyan]v{version}[/cyan] [dim]{commit_hash[:8]}[/dim]",
        f"[bold]{message}[/bold]",
        f"[dim]{timestamp} by {author}[/dim]",
    ]

    if changes:
        content_lines.append("")
        for key, value in changes.items():
            content_lines.append(f"  • {key}: {value}")

    panel = Panel(
        "\n".join(content_lines),
        border_style="cyan" if version > 0 else "green",
        padding=(1, 2),
    )
    console.print(panel)


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
