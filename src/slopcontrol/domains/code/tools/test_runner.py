"""Test runner and linting tools for the code domain."""

from __future__ import annotations

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


@tool
def run_tests(
    target: Optional[str] = None,
    project_path: Optional[str] = None,
    verbose: bool = False,
) -> str:
    """Run pytest for the project.

    Args:
        target: Specific file or directory.  If None, runs the whole test suite.
        project_path: Base directory.
        verbose: Add ``-v`` flag.

    Returns:
        Formatted test output.
    """
    base = Path(project_path) if project_path else Path.cwd()
    cmd = ["python", "-m", "pytest", "-q"]
    if verbose:
        cmd.append("-v")
    cmd.append(target or str(base))
    rc, out, err = _run(cmd, base)
    return f"Exit code: {rc}\n\n{out}\n{err}".strip()


@tool
def run_linter(
    paths: Optional[list[str]] = None,
    project_path: Optional[str] = None,
) -> str:
    """Run ``ruff check`` on the project.

    Args:
        paths: Files or directories to lint.  If None, lints ``src/`` and ``tests/``.
        project_path: Base directory.

    Returns:
        Ruff output.
    """
    base = Path(project_path) if project_path else Path.cwd()
    targets = paths or ["src", "tests"]
    cmd = ["ruff", "check"] + targets
    rc, out, err = _run(cmd, base)
    return f"Exit code: {rc}\n\n{out}\n{err}".strip()


@tool
def run_type_check(
    paths: Optional[list[str]] = None,
    project_path: Optional[str] = None,
) -> str:
    """Run ``mypy`` on the project.

    Args:
        paths: Files or directories.  If None, checks ``src/`` and ``tests/``.
        project_path: Base directory.

    Returns:
        Mypy output.
    """
    base = Path(project_path) if project_path else Path.cwd()
    targets = paths or ["src", "tests"]
    cmd = ["mypy", "--ignore-missing-imports"] + targets
    rc, out, err = _run(cmd, base)
    return f"Exit code: {rc}\n\n{out}\n{err}".strip()


TEST_TOOLS = [run_tests, run_linter, run_type_check]
