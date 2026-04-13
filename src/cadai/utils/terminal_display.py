"""Terminal display utilities for rendering images in the terminal."""

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


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


def display_image_ascii(img_path: str, max_height: int = 30) -> str:
    """Convert image to ASCII art representation.

    Args:
        img_path: Path to the image file
        max_height: Maximum height in characters

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
    img_array = np.array(img.convert("L"))

    chars = "@%#*+=-:. "
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
) -> None:
    """Display a preview image in a Rich panel.

    Args:
        image_path: Path to the preview image
        image_path: Title for the panel
        max_height: Maximum height for ASCII display
    """
    img_path = Path(image_path)

    if not img_path.exists():
        console.print(f"[red]Image not found: {image_path}[/red]")
        return

    ascii_art = display_image_ascii(str(img_path), max_height=max_height)

    panel = Panel(
        ascii_art,
        title=title,
        border_style="cyan",
        padding=(1, 1),
    )
    console.print(panel)


def display_multiview_previews(
    image_paths: dict[str, str],
    title: str = "Multi-View Preview",
) -> None:
    """Display multiple preview images side by side.

    Args:
        image_paths: Dict of view name to image path
        title: Title for the display
    """
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("View", style="cyan", width=20)

    views_data = {}
    for view_name, img_path in image_paths.items():
        if Path(img_path).exists():
            views_data[view_name] = display_image_ascii(img_path, max_height=20)

    if not views_data:
        console.print("[yellow]No preview images available[/yellow]")
        return

    max_lines = max(len(ascii.split("\n")) for ascii in views_data.values())

    for view_name, ascii in views_data.items():
        lines = ascii.split("\n")
        while len(lines) < max_lines:
            lines.append(" " * len(lines[0]) if lines else "")
        views_data[view_name] = "\n".join(lines)

    table.add_column("Preview", style="white", width=60)

    rows = []
    for view_name in views_data:
        rows.append(view_name)

    for row in rows:
        table.add_row(row, views_data[row])

    console.print(table)


def display_model_info_table(info: dict) -> None:
    """Display model information in a formatted table.

    Args:
        info: Model information dictionary
    """
    table = Table(title="Model Information", show_header=False)
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="white", width=30)

    for key, value in info.items():
        if isinstance(value, float):
            table.add_row(key, f"{value:.2f}")
        else:
            table.add_row(key, str(value))

    console.print(table)
