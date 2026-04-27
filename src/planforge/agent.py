"""PlanForge agent factory.

Provides backward-compatible :func:`create_cad_agent` plus a new
:func:`create_agent` that consults the Conductor / domain plugin system.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Union

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage


def create_cad_agent(
    model: Optional[Union[str, BaseChatModel]] = None,
    provider: str = "auto",
    project_dir: Optional[str] = None,
    **deepagents_kwargs: Any,
) -> Any:
    """Create a CAD-enabled agent (legacy — delegates to :func:`create_agent`)."""
    return create_agent(
        domain="cad",
        model=model,
        provider=provider,
        project_dir=project_dir,
        **deepagents_kwargs,
    )


def create_agent(
    domain: str = "cad",
    model: Optional[Union[str, BaseChatModel]] = None,
    provider: str = "auto",
    project_dir: Optional[str] = None,
    **deepagents_kwargs: Any,
) -> Any:
    """Create a domain-specific agent via the plugin registry.

    Args:
        domain: Plugin name, e.g. ``"cad"`` or ``"code"``.
        model: LLM model or model spec string.
        provider: LLM provider ("openai", "anthropic", "ollama", "auto").
        project_dir: Working directory.
        **deepagents_kwargs: Passed to ``deepagents.create_deep_agent``.

    Returns:
        Compiled LangGraph agent.
    """
    from planforge.core.domain_base import create_domain_agent
    from planforge.core.orchestrator.registry import PluginRegistry
    from planforge.core.providers.registry import get_model

    registry = PluginRegistry()
    registry.auto_discover()
    plugin = registry.get(domain)

    # Resolve model
    if model is None:
        model = os.environ.get("PLANFORGE_MODEL", "opencode:big-pickle")
    if isinstance(model, str):
        chat_model = get_model(model, provider=provider)
    else:
        chat_model = model

    return create_domain_agent(
        plugin=plugin,
        model=chat_model,
        project_dir=project_dir,
        **deepagents_kwargs,
    )


def run_design_session(
    prompt: str,
    model: Optional[str] = None,
    provider: str = "auto",
    project_dir: Optional[str] = None,
    interactive: bool = True,
) -> dict[str, Any]:
    """Run a single design session.

    If a ``plan_forge.md`` exists in the project directory, infers the
    domain from it; otherwise defaults to ``"cad"``.
    """
    resolved = Path(project_dir or os.environ.get("PLANFORGE_PROJECT_DIR", "./projects"))
    plan_path = resolved / "plan_forge.md"

    domain = "cad"
    if plan_path.exists():
        try:
            from planforge.core.plan.renderer import read_plan
            plan = read_plan(plan_path)
            domain = plan.domain
        except Exception:
            pass

    agent = create_agent(
        domain=domain,
        model=model,
        provider=provider,
        project_dir=str(resolved),
    )

    messages = [HumanMessage(content=prompt)]

    if interactive:
        result = agent.invoke({"messages": messages}, stream=True)
        return {"agent": agent, "stream": result}
    else:
        result = agent.invoke({"messages": messages})
        return {"agent": agent, "result": result}
