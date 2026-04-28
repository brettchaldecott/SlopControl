"""OpenCode integration adapter.

Invokes the local ``opencode`` CLI to run coding tasks based on a
SlopControl plan section.  The plan is the artifact; opencode is the
execution agent that produces the code product.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class OpenCodeAdapter:
    """Dispatch plan sections to the OpenCode agent."""

    def __init__(self, timeout: int = 300) -> None:
        self.timeout = timeout

    def execute(
        self,
        task: str,
        context_dir: Path | str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run ``opencode`` with the given task spec.

        Args:
            task: Natural language task description or structured spec.
            context_dir: Working directory for the agent.

        Returns:
            Dict with ``success``, ``stdout``, ``stderr``.
        """
        context_dir = Path(context_dir)
        context_dir.mkdir(parents=True, exist_ok=True)

        # Check if opencode is installed
        cmd = ["opencode", "--help"]
        try:
            subprocess.run(cmd, capture_output=True, timeout=5)
        except FileNotFoundError:
            logger.warning("OpenCode CLI not found; falling back to stdout print")
            return {
                "success": False,
                "stdout": "",
                "stderr": "OpenCode CLI not installed. Install with: npm install -g opencode",
            }

        # Build the actual command
        # OpenCode supports task file input
        args = [
            "opencode",
            "--task", task,
            "--context", str(context_dir),
        ]

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(context_dir),
            )
            success = result.returncode == 0
            if not success:
                logger.error("OpenCode failed with rc=%d: %s", result.returncode, result.stderr[:200])
            return {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"OpenCode timed out after {self.timeout}s",
            }
        except Exception as exc:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(exc),
            }
