"""Claude Code integration adapter.

Dispatches to the ``claude`` CLI (Anthropic's coding agent).
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from .base import AgentAdapter

logger = logging.getLogger(__name__)


class ClaudeAdapter(AgentAdapter):
    """Execute tasks using Claude Code CLI."""

    name = "claude"

    def __init__(self, timeout: int = 300) -> None:
        self.timeout = timeout

    def execute(
        self,
        task: str,
        context_dir: Path | str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        context_dir = Path(context_dir)
        context_dir.mkdir(parents=True, exist_ok=True)

        # Write task to a temp file that claude can read
        task_file = context_dir / ".slopcontrol_task.md"
        task_file.write_text(f"# Task\n\n{task}\n", encoding="utf-8")

        cmd = ["claude", "-p", str(task_file)]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(context_dir),
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Claude Code CLI not installed. https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview",
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": f"Timeout after {self.timeout}s"}
        except Exception as exc:
            return {"success": False, "stdout": "", "stderr": str(exc)}
        finally:
            # Clean up task file
            try:
                task_file.unlink()
            except OSError:
                pass
