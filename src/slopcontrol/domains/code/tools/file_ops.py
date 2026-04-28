"""File operations for code domain projects."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from langchain_core.tools import tool


@tool
def list_files(
    pattern: str = "*.py",
    project_path: Optional[str] = None,
) -> str:
    """List files matching a glob pattern.

    Args:
        pattern: Glob pattern (e.g. ``src/**/*.py``).
        project_path: Base directory.

    Returns:
        Newline-separated file paths.
    """
    base = Path(project_path) if project_path else Path.cwd()
    matches = sorted(base.glob(pattern))
    return "\n".join(str(p.relative_to(base)) for p in matches) or "No files found"


@tool
def create_module(
    name: str,
    project_path: Optional[str] = None,
) -> str:
    """Create a Python module (directory + ``__init__.py``).

    Args:
        name: Dot-separated module path, e.g. ``my_pkg.sub_mod``.
        project_path: Base directory.

    Returns:
        Confirmation message.
    """
    base = Path(project_path) if project_path else Path.cwd()
    parts = name.replace("-", "_").split(".")
    target = base / Path(*parts)
    try:
        target.mkdir(parents=True, exist_ok=True)
        init = target / "__init__.py"
        if not init.exists():
            init.write_text(f'"""{target.name} module."""\n')
        return f"Created module {name} at {target}"
    except Exception as exc:
        return f"Error creating module: {exc}"


@tool
def move_file(
    source: str,
    destination: str,
    project_path: Optional[str] = None,
) -> str:
    """Move or rename a file.

    Args:
        source: Original relative path.
        destination: New relative path.
        project_path: Base directory.

    Returns:
        Confirmation message.
    """
    base = Path(project_path) if project_path else Path.cwd()
    src = base / source
    dst = base / destination
    if not src.exists():
        return f"Error: Source '{source}' not found"
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        return f"Moved {source} -> {destination}"
    except Exception as exc:
        return f"Error moving file: {exc}"


@tool
def find_in_files(
    query: str,
    pattern: str = "*.py",
    project_path: Optional[str] = None,
) -> str:
    """Search for *query* in all files matching *pattern*.

    Args:
        query: String to search for.
        pattern: Glob pattern to limit search scope.
        project_path: Base directory.

    Returns:
        Matching lines with file and line number.
    """
    base = Path(project_path) if project_path else Path.cwd()
    results: list[str] = []
    for p in base.glob(pattern):
        if p.is_dir():
            continue
        try:
            for i, line in enumerate(p.read_text().splitlines(), 1):
                if query in line:
                    rel = p.relative_to(base)
                    results.append(f"{rel}:{i}: {line.strip()}")
        except Exception:
            continue
    return "\n".join(results[:50]) or "No matches found"


FILE_TOOLS = [list_files, create_module, move_file, find_in_files]
