"""Design iteration tracking and history management."""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class DesignIteration:
    """Represents a single design iteration."""

    version: int
    timestamp: str
    message: str
    model_info: dict
    snapshot_path: Optional[str] = None
    git_commit: Optional[str] = None
    changes: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DesignIteration":
        """Create from dictionary."""
        return cls(**data)


class DesignHistory:
    """Manages design iteration history for a project."""

    def __init__(self, project_path: Path):
        """Initialize design history manager.

        Args:
            project_path: Path to the project directory
        """
        self.project_path = project_path
        self.history_file = project_path / ".planforge" / "history.json"
        self.iterations: list[DesignIteration] = []
        self._load()

    def _load(self) -> None:
        """Load history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    data = json.load(f)
                    self.iterations = [DesignIteration.from_dict(item) for item in data]
            except Exception:
                self.iterations = []

    def _save(self) -> None:
        """Save history to file."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, "w") as f:
            json.dump([iter.to_dict() for iter in self.iterations], f, indent=2)

    def add_iteration(
        self,
        message: str,
        model_info: dict,
        snapshot_path: Optional[str] = None,
        git_commit: Optional[str] = None,
        changes: Optional[dict] = None,
    ) -> DesignIteration:
        """Add a new iteration.

        Args:
            message: Description of changes
            model_info: Model dimensions and properties
            snapshot_path: Path to preview image
            git_commit: Git commit hash
            changes: Dict of what changed

        Returns:
            The new DesignIteration
        """
        version = len(self.iterations) + 1
        iteration = DesignIteration(
            version=version,
            timestamp=datetime.now().isoformat(),
            message=message,
            model_info=model_info,
            snapshot_path=snapshot_path,
            git_commit=git_commit,
            changes=changes,
        )
        self.iterations.append(iteration)
        self._save()
        return iteration

    def get_iteration(self, version: int) -> Optional[DesignIteration]:
        """Get a specific iteration.

        Args:
            version: Version number

        Returns:
            DesignIteration or None
        """
        for iteration in self.iterations:
            if iteration.version == version:
                return iteration
        return None

    def get_latest(self) -> Optional[DesignIteration]:
        """Get the latest iteration.

        Returns:
            Most recent DesignIteration or None
        """
        return self.iterations[-1] if self.iterations else None

    def get_history(
        self,
        limit: Optional[int] = None,
    ) -> list[DesignIteration]:
        """Get iteration history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of iterations (most recent first)
        """
        history = list(reversed(self.iterations))
        if limit:
            history = history[:limit]
        return history

    def compare_versions(
        self,
        v1: int,
        v2: int,
    ) -> dict:
        """Compare two versions.

        Args:
            v1: First version number
            v2: Second version number

        Returns:
            Dict of differences
        """
        iter1 = self.get_iteration(v1)
        iter2 = self.get_iteration(v2)

        if not iter1 or not iter2:
            return {"error": "Version not found"}

        info1 = iter1.model_info or {}
        info2 = iter2.model_info or {}

        dims1 = info1.get("dimensions", {})
        dims2 = info2.get("dimensions", {})

        differences = {
            "version_1": v1,
            "version_2": v2,
            "dimensions": {},
            "properties": {},
        }

        for dim in ["width", "height", "depth"]:
            val1 = dims1.get(dim, 0)
            val2 = dims2.get(dim, 0)
            diff = val2 - val1
            if abs(diff) > 0.001:
                differences["dimensions"][dim] = {
                    "before": val1,
                    "after": val2,
                    "change": diff,
                }

        for prop in ["volume", "surface_area"]:
            val1 = info1.get(prop, 0)
            val2 = info2.get(prop, 0)
            diff = val2 - val1
            if abs(diff) > 0.001:
                differences["properties"][prop] = {
                    "before": val1,
                    "after": val2,
                    "change": diff,
                }

        return differences

    def get_summary(self) -> dict:
        """Get summary statistics.

        Returns:
            Dict with summary info
        """
        if not self.iterations:
            return {
                "total_iterations": 0,
                "first_version": None,
                "latest_version": None,
            }

        latest = self.get_latest()
        return {
            "total_iterations": len(self.iterations),
            "first_version": self.iterations[0].version if self.iterations else None,
            "latest_version": latest.version if latest else None,
            "first_timestamp": self.iterations[0].timestamp if self.iterations else None,
            "latest_timestamp": latest.timestamp if latest else None,
        }

    def format_for_display(self, limit: Optional[int] = 10) -> str:
        """Format history for terminal display.

        Args:
            limit: Maximum entries to show

        Returns:
            Formatted string
        """
        from ..utils.terminal_display import display_design_history_entry

        history = self.get_history(limit=limit)

        if not history:
            return "No design history yet."

        lines = ["[bold cyan]Design History[/bold cyan]", "=" * 50, ""]

        for iteration in history:
            display_design_history_entry(
                version=iteration.version,
                commit_hash=iteration.git_commit or "local",
                message=iteration.message,
                timestamp=iteration.timestamp,
                changes=iteration.changes,
            )
            lines.append("")

        return "\n".join(lines)
