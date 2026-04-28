"""Abstract base for domain execution sessions.

A ``DomainSession`` wraps an active agent working on a plan section.
It persists state across iterations so the conductor can resume,
pause, or hand off work to another domain.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class DomainSession(ABC):
    """Persistent execution context for a single domain agent.

    Created by the Conductor when it dispatches a plan section.
    Maintains conversation history, intermediate artifacts, and
    checkpointable state.
    """

    def __init__(
        self,
        project_path: Path,
        plugin_name: str,
    ) -> None:
        self.project_path = project_path
        self.plugin_name = plugin_name
        self._history: list[dict] = []

    # -- Lifecycle -----------------------------------------------------

    @abstractmethod
    def start(self, plan_section: dict[str, Any]) -> None:
        """Initialise the session with the section that must be executed."""
        ...

    @abstractmethod
    def iteration(self, user_input: str) -> str:
        """Run one turn of the agent loop.

        Args:
            user_input: The user's natural-language message for this turn.

        Returns:
            The agent's response as a string.
        """
        ...

    # -- Artifacts -----------------------------------------------------

    @abstractmethod
    def export(self) -> list[dict[str, Any]]:
        """Return metadata about every artifact produced so far.

        Each dict should contain at least ``path``, ``type``, and
        ``description`` keys.
        """
        ...

    # -- Persistence ---------------------------------------------------

    def checkpoint(self) -> dict[str, Any]:
        """Serialise session state so it can be resumed later.

        Subclasses should call ``super().checkpoint()`` and then
        add their own keys.
        """
        return {
            "plugin_name": self.plugin_name,
            "project_path": str(self.project_path),
            "history": self._history,
        }

    def restore(self, state: dict[str, Any]) -> None:
        """Restore session from a checkpoint dict."""
        self.plugin_name = state.get("plugin_name", self.plugin_name)
        self.project_path = Path(state.get("project_path", self.project_path))
        self._history = state.get("history", [])

    # -- History helpers -----------------------------------------------

    def record_turn(self, role: str, content: str) -> None:
        """Append a conversational turn to internal history."""
        self._history.append({"role": role, "content": content})
