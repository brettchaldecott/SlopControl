"""Code domain tools — read, write, edit source files."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from langchain_core.tools import tool


@tool
def read_code(
    path: str,
    project_path: Optional[str] = None,
    offset: int = 1,
    limit: Optional[int] = None,
) -> str:
    """Read the contents of a source file.

    Args:
        path: Relative or absolute path to the file.
        project_path: Base directory for relative paths.
        offset: Line number to start from (1-indexed).
        limit: Max lines to read.  If None, reads whole file.

    Returns:
        File contents as a string.
    """
    base = Path(project_path) if project_path else Path.cwd()
    target = base / path
    if not target.exists():
        return f"Error: File '{path}' not found"
    try:
        lines = target.read_text().splitlines()
        start = max(0, offset - 1)
        end = len(lines) if limit is None else start + limit
        return "\n".join(lines[start:end])
    except Exception as exc:
        return f"Error reading file: {exc}"


@tool
def write_code(
    path: str,
    content: str,
    project_path: Optional[str] = None,
) -> str:
    """Write code to a file (creates directories automatically).

    Args:
        path: Relative or absolute file path.
        content: Full source code to write.
        project_path: Base directory for relative paths.

    Returns:
        Confirmation message.
    """
    base = Path(project_path) if project_path else Path.cwd()
    target = base / path
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"Wrote {target}"
    except Exception as exc:
        return f"Error writing file: {exc}"


@tool
def edit_code(
    path: str,
    old_string: str,
    new_string: str,
    project_path: Optional[str] = None,
) -> str:
    """Replace *old_string* with *new_string* in a file.

    Use this for surgical changes without rewriting the whole file.

    Args:
        path: Path to the file.
        old_string: Exact text to replace.
        new_string: Replacement text.
        project_path: Base directory for relative paths.

    Returns:
        Confirmation or error message.
    """
    base = Path(project_path) if project_path else Path.cwd()
    target = base / path
    if not target.exists():
        return f"Error: File '{path}' not found"
    try:
        text = target.read_text()
        if old_string not in text:
            return f"Error: old_string not found in {path}"
        new_text = text.replace(old_string, new_string, 1)
        target.write_text(new_text)
        return f"Edited {path}"
    except Exception as exc:
        return f"Error editing file: {exc}"


@tool
def delete_file(
    path: str,
    project_path: Optional[str] = None,
) -> str:
    """Delete a file from the project.

    Args:
        path: File path.
        project_path: Base directory.

    Returns:
        Confirmation message.
    """
    base = Path(project_path) if project_path else Path.cwd()
    target = base / path
    if not target.exists():
        return f"Error: File '{path}' not found"
    try:
        target.unlink()
        return f"Deleted {target}"
    except Exception as exc:
        return f"Error deleting file: {exc}"


CODE_TOOLS = [read_code, write_code, edit_code, delete_file]
