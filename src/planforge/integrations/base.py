"""Abstract base for all agent integration adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class AgentAdapter(ABC):
    """Execute a plan section using an external AI coding agent."""

    name: str = "abstract"

    @abstractmethod
    def execute(
        self,
        task: str,
        context_dir: Path | str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run the agent with the given task.

        Args:
            task: Description of the work to perform.
            context_dir: Working directory for the agent.

        Returns:
            Dict with ``success``, ``stdout``, ``stderr``, ``returncode``.
        """
        ...
