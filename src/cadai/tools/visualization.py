"""Visualization tools for CAD preview and terminal display."""

import os
import tempfile
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

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
    from ..utils.cad_helpers import deserialize_body

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
def display_preview_in_terminal(image_path: str) -> str:
    """Display a preview image in the terminal using ANSI escape codes.

    Args:
        image_path: Path to the PNG image

    Returns:
        Confirmation message
    """
    _check_llmcad()

    img_path = Path(image_path)
    if not img_path.exists():
        return f"Error: Image not found at {image_path}"

    try:
        img = Image.open(img_path)

        max_width = 120
        max_height = 40

        img_ratio = img.width / img.height
        if img.width > max_width:
            new_width = max_width
            new_height = int(max_width / img_ratio)
            img = img.resize((new_width, new_height))
        if img.height > max_height:
            new_height = max_height
            new_width = int(max_height * img_ratio)
            img = img.resize((new_width, new_height))

        img_path_str = str(img_path.absolute())
        return f"[Preview image available at: {img_path_str}]"

    except Exception as e:
        return f"Error displaying image: {str(e)}"


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
        f"Model: {data.get('name', 'unnamed')}",
        "=" * 40,
        "Dimensions:",
        f"  Width:  {info.get('dimensions', {}).get('width', 'N/A'):.2f} mm",
        f"  Height: {info.get('dimensions', {}).get('height', 'N/A'):.2f} mm",
        f"  Depth:  {info.get('dimensions', {}).get('depth', 'N/A'):.2f} mm",
        "",
        "Properties:",
        f"  Volume:       {info.get('volume', 'N/A'):.2f} mm³",
        f"  Surface Area: {info.get('surface_area', 'N/A'):.2f} mm²",
        f"  Faces:        {info.get('face_count', 'N/A')}",
        f"  Edges:        {info.get('edge_count', 'N/A')}",
    ]

    return "\n".join(lines)


VISUALIZATION_TOOLS = [
    render_preview,
    display_preview_in_terminal,
    get_model_info_detailed,
]
