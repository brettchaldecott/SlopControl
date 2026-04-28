"""Section-to-agent dispatch logic for the Conductor."""

from __future__ import annotations

import logging
from typing import Any

from slopcontrol.core.domain_base.plugin import DomainPlugin
from slopcontrol.core.plan.schema import DesignPlan

from .protocol import AgentType
from .registry import PluginRegistry

logger = logging.getLogger(__name__)


class DispatchEngine:
    """Decides which agent (internal domain or external adapter) should
    handle each step of a :class:`~slopcontrol.core.plan.schema.DesignPlan`.
    """

    def __init__(self, registry: PluginRegistry) -> None:
        self.registry = registry

    # -- Public API -----------------------------------------------------

    def select_agent(
        self,
        step: dict[str, Any],
        plan: DesignPlan,
    ) -> tuple[str, AgentType]:
        """Return ``(agent_name, agent_type)`` for *step*.

        Resolution order:
        1. Explicit ``step["domain"]`` or ``step["agent"]`` field.
        2. Inferred from step description via keyword matching.
        3. Fallback to the plan's top-level ``domain``.
        """
        # 1. Explicit domain/agent field
        domain = step.get("domain")
        agent = step.get("agent")

        if domain and self.registry.has(domain):
            return domain, AgentType.INTERNAL_DOMAIN

        if agent:
            if self.registry.has(agent):
                return agent, AgentType.INTERNAL_DOMAIN
            if self.registry.get_external_adapter(agent):
                return agent, AgentType.EXTERNAL_ADAPTER

        # 2. Infer from keywords
        inferred = self._infer_domain(step.get("description", ""))
        if inferred and self.registry.has(inferred):
            return inferred, AgentType.INTERNAL_DOMAIN

        # 3. Fallback to plan-level domain
        if self.registry.has(plan.domain):
            return plan.domain, AgentType.INTERNAL_DOMAIN

        raise OrchestrationError(
            f"Cannot dispatch step: no agent for domain '{domain or inferred or plan.domain}'"
        )

    # -- Inference helpers ----------------------------------------------

    def _infer_domain(self, description: str) -> str | None:
        """Very lightweight keyword-based inference.

        In the future this can be replaced by an LLM call, but for now
        simple keyword matching is fast and deterministic.
        """
        text = description.lower()
        scores: dict[str, int] = {}

        for name, plugin in self.registry.all().items():
            score = 0
            for cap in plugin.get_capabilities():
                if cap.lower() in text:
                    score += 1
            if score:
                scores[name] = score

        if scores:
            return max(scores, key=scores.get)  # type: ignore[arg-type]
        return None


class OrchestrationError(Exception):
    """Raised when the Conductor cannot proceed."""
    pass
