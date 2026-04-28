"""Plan loader – thin wrapper around ``PlanRenderer.read()``.

Future: async loader, remote plan fetching, validation hooks.
"""

from __future__ import annotations

from pathlib import Path

from .renderer import PlanRenderer
from .schema import DesignPlan


class PlanLoader:
    """Load ``plan_forge.md`` from disk."""

    def __init__(self, renderer: PlanRenderer | None = None) -> None:
        self.renderer = renderer or PlanRenderer()

    def load(self, path: Path) -> DesignPlan:
        """Read and validate a plan artifact."""
        if not path.exists():
            raise FileNotFoundError(f"Plan file not found: {path}")
        return self.renderer.read(path)


# Convenience

def load_plan(path: Path) -> DesignPlan:
    return PlanLoader().load(path)
