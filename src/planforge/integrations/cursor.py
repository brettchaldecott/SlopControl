"""Cursor integration adapter.

Cursor lacks a headless CLI for task execution; this adapter
produces a task manifest that the user can load into Cursor.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .base import AgentAdapter

logger = logging.getLogger(__name__)


class CursorAdapter(AgentAdapter):
    """Generate a Cursor-compatible task manifest."""

    name = "cursor"

    def execute(
        self,
        task: str,
        context_dir: Path | str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        context_dir = Path(context_dir)
        context_dir.mkdir(parents=True, exist_ok=True)

        # Cursor doesn't have a CLI; generate a manifest
        manifest = {
            "agent": "cursor",
            "task": task,
            "context_dir": str(context_dir),
            "instructions": "Open this directory in Cursor and paste the task into Composer.",
        }
        manifest_path = context_dir / ".cursor_task.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        return {
            "success": True,
            "stdout": f"Cursor task manifest written to {manifest_path}",
            "stderr": (
                "Cursor does not support headless execution.\n"
                "Open the project in Cursor and use Composer with the task description.\n"
                f"Manifest: {manifest_path}"
            ),
            "manifest": str(manifest_path),
        }
