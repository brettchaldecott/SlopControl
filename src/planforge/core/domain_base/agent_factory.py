"""Factory that assembles a domain-specific deep agent.

Wraps ``deepagents.create_deep_agent()`` with the correct tools,
system prompt, filesystem backend, and skill directories from a
registered :class:`~plugin.DomainPlugin`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel

from .plugin import DomainPlugin


def create_domain_agent(
    plugin: DomainPlugin,
    model: BaseChatModel | None = None,
    project_dir: Path | str | None = None,
    **deepagents_kwargs: Any,
) -> Any:
    """Build a deepagents LangGraph agent configured for *plugin*.

    Args:
        plugin: The domain plugin whose tools / prompt / skills are used.
        model: LLM model (defaults to ``PLANFORGE_MODEL`` → gateway).
        project_dir: Working directory for the agent (default ``./projects``).
        **deepagents_kwargs: Passed through to ``create_deep_agent``.

    Returns:
        Compiled LangGraph agent.
    """
    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend

    if model is None:
        from planforge.core.providers.registry import get_model
        model = get_model(os.environ.get("PLANFORGE_MODEL"))

    resolved_dir = Path(project_dir or os.environ.get("PLANFORGE_PROJECT_DIR", "./projects"))
    backend = FilesystemBackend(root_dir=str(resolved_dir))

    system_prompt = plugin.get_agent_prompt()

    skills_dirs = []
    skills_path = plugin.get_skills_dir()
    if skills_path:
        skills_dirs.append(str(skills_path))

    return create_deep_agent(
        model=model,
        tools=plugin.get_tools(),
        system_prompt=system_prompt,
        backend=backend,
        skills=skills_dirs if skills_dirs else None,
        **deepagents_kwargs,
    )
