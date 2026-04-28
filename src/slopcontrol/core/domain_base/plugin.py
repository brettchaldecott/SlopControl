"""Abstract base for domain plugins.

Every domain (code, pcb, firmware, etc.) implements a ``DomainPlugin``.
The plugin provides the Conductor with all domain-specific assets:
tools, verifiers, prompts, and project scaffolding.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class DomainPlugin(ABC):
    """Contract for a SlopControl domain plugin.

    A domain is a vertical expertise area (software, web, firmware, etc.).
    The Conductor loads plugins via
    :class:`~slopcontrol.core.orchestrator.registry.PluginRegistry` and
    uses them to dispatch plan sections to the right agents.
    """

    # Identifiers -------------------------------------------------------
    name: str = "abstract"          # e.g. "code", "web"
    display_name: str = "Abstract"  # e.g. "Software Development"

    # -- Tools --------------------------------------------------------
    @abstractmethod
    def get_tools(self) -> list[Any]:
        """Return LangChain ``@tool`` functions for this domain.

        These are fed directly to ``deepagents.create_deep_agent()``.
        """
        ...

    # -- Verification -------------------------------------------------
    def get_verifiers(self) -> list[Any]:
        """Return verifier instances for this domain.

        Each verifier must inherit from
        :class:`~slopcontrol.core.verify.base.DomainVerifier`.
        """
        return []

    # -- Agent identity ------------------------------------------------
    def get_agent_prompt(self) -> str:
        """Return the system prompt for an agent working in this domain.

        If a file ``agent_prompt.md`` exists next to the plugin module it
        is read automatically; subclasses may override.
        """
        prompt_path = Path(self._prompt_path())
        if prompt_path.exists():
            return prompt_path.read_text()
        return f"You are a SlopControl agent specialising in {self.display_name}."

    # -- Skills --------------------------------------------------------
    def get_skills_dir(self) -> Path | None:
        """Directory with skill markdown files for deepagents."""
        candidate = Path(self._base_dir()) / "skills"
        return candidate if candidate.exists() else None

    # -- Project scaffolding -------------------------------------------
    def scaffold_project(self, project_path: Path) -> None:
        """Create domain-specific directories under *project_path*.

        Examples: ``src/``, ``tests/``, ``docs/`` for software.
        """
        ...

    # -- Capabilities metadata -----------------------------------------
    def get_capabilities(self) -> list[str]:
        """Return capability tags for planning and routing.
        """
        return []

    # -- Prompt path helper --------------------------------------------
    def _prompt_path(self) -> Path:
        """Resolve the default ``agent_prompt.md`` path."""
        return Path(self._base_dir()) / "agent_prompt.md"

    def _base_dir(self) -> Path:
        """Directory that contains the concrete plugin module."""
        import inspect
        mod = inspect.getmodule(self)
        assert mod is not None and mod.__file__ is not None
        return Path(mod.__file__).parent
