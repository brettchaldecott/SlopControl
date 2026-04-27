"""Checkpoint / resume support for orchestration state."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from planforge.core.plan.renderer import read_plan

from .protocol import HandoffArtifact
from .state import OrchestrationState

logger = logging.getLogger(__name__)

_STATE_FILE = "orchestration_state.json"


def save(state: OrchestrationState, project_dir: Path) -> Path:
    """Serialise *state* to ``.planforge/orchestration_state.json``."""
    out = project_dir / ".planforge" / _STATE_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state.to_dict(), indent=2))
    logger.info("Saved orchestration state to %s", out)
    return out


def load(project_dir: Path) -> OrchestrationState:
    """Restore :class:`OrchestrationState` from disk.

    Raises:
        FileNotFoundError: if no checkpoint exists.
    """
    src = project_dir / ".planforge" / _STATE_FILE
    if not src.exists():
        raise FileNotFoundError(f"No orchestration state found at {src}")

    data = json.loads(src.read_text())
    plan = read_plan(project_dir / "plan_forge.md")

    state = OrchestrationState(
        plan=plan,
        project_dir=project_dir,
        current_step=data.get("current_step", 0),
        step_states=data.get("step_states", []),
        artifacts=data.get("artifacts", []),
        verification_results=[],  # Recomputed on resume
        error_log=data.get("error_log", []),
        metadata=data.get("metadata", {}),
    )

    # Restore handoffs
    state.handoffs = [
        HandoffArtifact.from_dict(h) for h in data.get("handoffs", [])
    ]

    logger.info("Loaded orchestration state from %s", src)
    return state


def exists(project_dir: Path) -> bool:
    return (project_dir / ".planforge" / _STATE_FILE).exists()
