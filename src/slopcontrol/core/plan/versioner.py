"""Plan versioner – append-only versioning with git + snapshot files.

Strategy:
- The working ``slop_control.md`` is the current version.
- Git tracks every change.
- Snapshot files (``slop_control_v1.0.md`` …) are created explicitly
  for human browsing.  This mirrors how Obsidian versions notes.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from .renderer import PlanRenderer
from .schema import DesignPlan

logger = logging.getLogger(__name__)


class PlanVersioner:
    """Manage append-only plan versioning."""

    def __init__(self, renderer: PlanRenderer | None = None) -> None:
        self.renderer = renderer or PlanRenderer()

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def save(self, plan: DesignPlan, project_dir: Path, message: str = "") -> Path:
        """Save the plan, snapshot old version, and git-commit.

        Returns: path to the saved ``slop_control.md``.
        """
        plan_path = self._plan_path(project_dir)
        snap = self._snapshot_path(project_dir, plan.version)

        # 1. Snapshot current working file if it exists
        if plan_path.exists():
            if not snap.exists():
                snap.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(plan_path, snap)

        # 2. Write new plan
        self.renderer.write(plan, plan_path)

        # 3. Git commit (best-effort)
        self._git_commit(project_dir, message or f"plan: update to v{plan.version}")

        return plan_path

    def archive(self, project_dir: Path, version: str) -> Path:
        """Create an explicit snapshot file for a given version."""
        plan_path = self._plan_path(project_dir)
        if not plan_path.exists():
            raise FileNotFoundError(plan_path)
        snap = self._snapshot_path(project_dir, version)
        snap.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(plan_path, snap)
        return snap

    def load_version(self, project_dir: Path, version: str) -> DesignPlan:
        """Load a snapshot as a read-only historical plan."""
        snap = self._snapshot_path(project_dir, version)
        if not snap.exists():
            raise FileNotFoundError(f"Snapshot v{version} not found: {snap}")
        return self.renderer.read(snap)

    # ----------------------------------------------------------------
    # Git helpers
    # ----------------------------------------------------------------

    def _git_commit(self, project_dir: Path, message: str) -> None:
        import subprocess

        try:
            subprocess.run(
                ["git", "add", "slop_control.md", "slop_control_*.md"],
                cwd=project_dir,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=project_dir,
                check=False,
                capture_output=True,
            )
        except FileNotFoundError:
            logger.debug("Git not available in %s; skipping auto-commit", project_dir)
        except Exception as exc:
            logger.debug("Git commit failed (likely nothing staged): %s", exc)

    # ----------------------------------------------------------------
    # Paths
    # ----------------------------------------------------------------

    @staticmethod
    def _plan_path(project_dir: Path) -> Path:
        return project_dir / "slop_control.md"

    @staticmethod
    def _snapshot_path(project_dir: Path, version: str) -> Path:
        return project_dir / f"slop_control_{version}.md"
