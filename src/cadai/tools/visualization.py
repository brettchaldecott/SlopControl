"""Visualization tools for CAD preview and terminal display."""

import os
import tempfile
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

from ..utils.cad_helpers import deserialize_body
from ..utils.terminal_display import display_preview_panel, display_multiview_previews

try:
    from llmcad import snapshot
    from PIL import Image

    LLM_CAD_AVAILABLE = True
except ImportError:
    LLM_CAD_AVAILABLE = False


def _check_llmcad() -> None:
    """Check if llmcad is available."""
    if not LLM_CAD_AVAILABLE:
        raise ImportError("llmcad is required for visualization. Install with: pip install llmcad")


@tool
def render_preview(
    body_data: str,
    filename: str = "preview",
    views: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> str:
    """Render a multi-view preview image of a CAD body.

    Renders views from multiple angles: front, back, left, right, top, bottom, and isometric.
    The image is saved as a PNG file and can be displayed using display_preview.

    Args:
        body_data: JSON data containing the body
        filename: Output filename (without extension)
        views: Comma-separated views to render (front, back, left, right, top, bottom, iso)
               If None, renders all views
        output_dir: Directory to save image (default: temp directory)

    Returns:
        Path to the rendered PNG image
    """
    import json

    _check_llmcad()

    data = json.loads(body_data)
    body = deserialize_body(body_data)["body"]

    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path(tempfile.gettempdir()) / "cadai_previews"
        output_path.mkdir(parents=True, exist_ok=True)

    view_list = None
    if views:
        view_list = [v.strip().lower() for v in views.split(",")]

    png_path = snapshot(
        body,
        filename=str(output_path / filename),
        views=view_list,
    )

    return str(png_path)


@tool
def display_preview(
    image_path: str,
    title: str = "Preview",
    max_height: int = 30,
) -> str:
    """Display a preview image in the terminal using ASCII art.

    Args:
        image_path: Path to the PNG image
        title: Title to display above the preview
        max_height: Maximum height for ASCII display (default 30 lines)

    Returns:
        Confirmation message with image path
    """
    _check_llmcad()

    img_path = Path(image_path)

    if not img_path.exists():
        return f"Error: Image not found at {image_path}"

    display_preview_panel(str(img_path), title=title, max_height=max_height)

    return f"Displayed preview: {image_path}"


@tool
def display_multiview(
    preview_path: str,
    views: Optional[str] = None,
) -> str:
    """Display multiple preview views in a table format.

    Args:
        preview_path: Path to the multi-view preview image
        views: Optional comma-separated list of specific views to display

    Returns:
        Confirmation message
    """
    _check_llmcad()

    img_path = Path(preview_path)

    if not img_path.exists():
        return f"Error: Preview image not found at {preview_path}"

    view_names = views.split(",") if views else ["front", "right", "top", "iso"]

    display_multiview_previews(
        {name.strip(): str(img_path) for name in view_names},
        title="Multi-View Preview",
    )

    return f"Displayed multi-view preview: {preview_path}"


@tool
def get_model_info_detailed(body_data: str) -> str:
    """Get detailed information about a CAD model.

    Args:
        body_data: JSON data containing the body

    Returns:
        Formatted string with model information
    """
    import json
    from ..utils.cad_helpers import get_model_info

    data = json.loads(body_data)
    body = data["body"]

    info = get_model_info(body)

    lines = [
        f"[bold cyan]Model:[/bold cyan] {data.get('name', 'unnamed')}",
        "[bold]Dimensions:[/bold]",
        f"  Width:  {info.get('dimensions', {}).get('width', 'N/A'):.2f} mm",
        f"  Height: {info.get('dimensions', {}).get('height', 'N/A'):.2f} mm",
        f"  Depth:  {info.get('dimensions', {}).get('depth', 'N/A'):.2f} mm",
        "",
        "[bold]Properties:[/bold]",
        f"  Volume:       {info.get('volume', 'N/A'):.2f} mm³",
        f"  Surface Area: {info.get('surface_area', 'N/A'):.2f} mm²",
        f"  Faces:        {info.get('face_count', 'N/A')}",
        f"  Edges:        {info.get('edge_count', 'N/A')}",
    ]

    return "\n".join(lines)


@tool
def compare_designs(
    design1_path: str,
    design2_path: str,
    output_path: Optional[str] = None,
) -> str:
    """Compare two designs and highlight differences.

    Args:
        design1_path: Path to first design (older version)
        design2_path: Path to second design (newer version)
        output_path: Optional path for comparison output

    Returns:
        Comparison result with dimension differences
    """
    import json
    from ..utils.cad_helpers import get_model_info, deserialize_body

    try:
        with open(design1_path) as f:
            data1 = json.load(f)
        with open(design2_path) as f:
            data2 = json.load(f)
    except Exception as e:
        return f"Error loading designs: {str(e)}"

    body1 = deserialize_body(json.dumps(data1))["body"]
    body2 = deserialize_body(json.dumps(data2))["body"]

    info1 = get_model_info(body1)
    info2 = get_model_info(body2)

    dims1 = info1.get("dimensions", {})
    dims2 = info2.get("dimensions", {})

    lines = [
        "[bold cyan]Design Comparison[/bold cyan]",
        "=" * 40,
        "",
        "[bold]Design 1:[/bold] {}\n[bold]Design 2:[/bold] {}".format(
            data1.get("name", "unnamed"),
            data2.get("name", "unnamed"),
        ),
        "",
        "[bold]Dimension Changes:[/bold]",
    ]

    for dim in ["width", "height", "depth"]:
        val1 = dims1.get(dim, 0)
        val2 = dims2.get(dim, 0)
        diff = val2 - val1
        if abs(diff) > 0.01:
            sign = "+" if diff > 0 else ""
            lines.append(f"  {dim.capitalize()}: {val1:.2f} → {val2:.2f} ({sign}{diff:.2f} mm)")
        else:
            lines.append(f"  {dim.capitalize()}: {val1:.2f} mm (unchanged)")

    vol1 = info1.get("volume", 0)
    vol2 = info2.get("volume", 0)
    vol_diff = vol2 - vol1
    lines.extend(
        [
            "",
            f"[bold]Volume:[/bold] {vol1:.2f} → {vol2:.2f} mm³ ({'+' if vol_diff > 0 else ''}{vol_diff:.2f})",
        ]
    )

    return "\n".join(lines)


VISUALIZATION_TOOLS = [
    render_preview,
    display_preview,
    display_multiview,
    get_model_info_detailed,
    compare_designs,
]
