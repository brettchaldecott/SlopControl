"""Dependency management tools for the code domain."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool


def _run(cmd: list[str], cwd: Path, timeout: int = 120) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


def _detect_manager(project_path: Path) -> str:
    """Detect dependency manager: ``pip``, ``poetry``, or ``uv``."""
    if (project_path / "poetry.lock").exists() or (project_path / "pyproject.toml").exists():
        pyproject = project_path / "pyproject.toml"
        if pyproject.exists():
            text = pyproject.read_text()
            if "poetry" in text:
                return "poetry"
            if "uv" in text:
                return "uv"
    if (project_path / "requirements.txt").exists():
        return "pip"
    return "pip"


@tool
def add_dependency(
    package: str,
    version: Optional[str] = None,
    dev: bool = False,
    project_path: Optional[str] = None,
) -> str:
    """Add a package dependency.

    Args:
        package: Package name on PyPI.
        version: Version specifier (e.g. ``>=1.0``).
        dev: Add as a dev dependency.
        project_path: Base directory.

    Returns:
        Command output.
    """
    base = Path(project_path) if project_path else Path.cwd()
    manager = _detect_manager(base)
    spec = f"{package}{version}" if version else package

    if manager == "poetry":
        cmd = ["poetry", "add"]
        if dev:
            cmd.append("--group=dev")
        cmd.append(spec)
    elif manager == "uv":
        cmd = ["uv", "add"]
        if dev:
            cmd.append("--dev")
        cmd.append(spec)
    else:
        req_file = base / "requirements.txt"
        if req_file.exists():
            with open(req_file, "a") as f:
                f.write(f"\n{spec}\n")
            return f"Appended {spec} to requirements.txt"
        return "Error: No requirements.txt found. Create one first or use poetry/uv."

    rc, out, err = _run(cmd, base)
    return f"Exit code: {rc}\n\n{out}\n{err}".strip()


@tool
def remove_dependency(
    package: str,
    dev: bool = False,
    project_path: Optional[str] = None,
) -> str:
    """Remove a package dependency.

    Args:
        package: Package name.
        dev: Remove from dev dependencies.
        project_path: Base directory.

    Returns:
        Command output.
    """
    base = Path(project_path) if project_path else Path.cwd()
    manager = _detect_manager(base)

    if manager == "poetry":
        cmd = ["poetry", "remove"]
        if dev:
            cmd.append("--group=dev")
        cmd.append(package)
    elif manager == "uv":
        cmd = ["uv", "remove"]
        if dev:
            cmd.append("--dev")
        cmd.append(package)
    else:
        req_file = base / "requirements.txt"
        if not req_file.exists():
            return "Error: No requirements.txt found"
        lines = req_file.read_text().splitlines()
        filtered = [ln for ln in lines if not ln.strip().startswith(package)]
        req_file.write_text("\n".join(filtered))
        return f"Removed {package} from requirements.txt"

    rc, out, err = _run(cmd, base)
    return f"Exit code: {rc}\n\n{out}\n{err}".strip()


@tool
def list_dependencies(project_path: Optional[str] = None) -> str:
    """List installed dependencies.

    Args:
        project_path: Base directory.

    Returns:
        Dependency list.
    """
    base = Path(project_path) if project_path else Path.cwd()
    manager = _detect_manager(base)

    if manager in ("poetry", "uv"):
        cmd = [manager, "show"]
        rc, out, err = _run(cmd, base)
        return f"Exit code: {rc}\n\n{out}\n{err}".strip()

    req_file = base / "requirements.txt"
    if req_file.exists():
        return req_file.read_text()

    # Try pip freeze as last resort
    rc, out, err = _run(["pip", "freeze"], base)
    return out if rc == 0 else f"Error: {err}"


DEP_TOOLS = [add_dependency, remove_dependency, list_dependencies]
