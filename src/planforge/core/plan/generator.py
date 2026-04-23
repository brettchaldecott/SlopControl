"""Plan generator – LLM prompt that converts requirements into a DesignPlan.

Uses the local gateway and knowledge base for context.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from planforge.core.gateway.config import GatewayConfig
from planforge.core.gateway.fallback import create_fallback_chain
from planforge.core.knowledge.retriever import KnowledgeRetriever

from .schema import DesignPlan

logger = logging.getLogger(__name__)

PLAN_GENERATION_PROMPT = """You are PlanForge's planning agent.
Your job is to take user requirements and turn them into a structured DesignPlan.

You have access to the following knowledge base context:
{kb_context}

User request: {request}
Domain: {domain}

Generate a DesignPlan with:
1. Clear requirements (bullet points)
2. Design decisions (each with title, decision, rationale)
3. Implementation steps (ordered, with script references if applicable)
4. A verification table (version 1.0 initial checks)

Output ONLY valid JSON matching this schema:
{{
  "requirements": [str],
  "decisions": [{{"title": str, "decision": str, "rationale": str, ...}}],
  "implementation_steps": [{{"description": str, "script": str | null, ...}}],
  "verification_log": [{{"version": "1.0", "check": str, "result": "pending", "notes": str}}]
}}
"""


class PlanGenerator:
    """Generate DesignPlan from user requirements using the gateway + KB."""

    def __init__(
        self,
        model: BaseChatModel | None = None,
        retriever: KnowledgeRetriever | None = None,
    ) -> None:
        self.model = model or self._default_model()
        self.retriever = retriever

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def generate(
        self,
        request: str,
        domain: str = "cad",
        name: str = "",
        tags: list[str] | None = None,
        agents: list[str] | None = None,
    ) -> DesignPlan:
        """Generate a new DesignPlan from a user request."""
        # 1. Build KB context
        kb_context = ""
        if self.retriever:
            kb_context = self.retriever.get_context_string(query=request, k=3)

        # 2. Call LLM via gateway
        prompt = PLAN_GENERATION_PROMPT.format(
            kb_context=kb_context or "(no knowledge base context available)",
            request=request,
            domain=domain,
        )

        response = self.model.invoke([SystemMessage(content=prompt)])
        content = response.content if isinstance(response.content, str) else str(response.content)

        # 3. Parse JSON from response
        plan_dict = self._extract_json(content)

        # 4. Build DesignPlan
        return DesignPlan(
            name=name or self._slugify(request),
            domain=domain,
            tags=tags or [],
            agents=agents or ["planforge"],
            requirements=plan_dict.get("requirements", []),
            decisions=plan_dict.get("decisions", []),
            implementation_steps=plan_dict.get("implementation_steps", []),
            verification_log=plan_dict.get("verification_log", []),
        )

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def _default_model(self) -> BaseChatModel:
        """Create a default model via the gateway."""
        from langchain_openai import ChatOpenAI

        cfg = GatewayConfig.from_env()
        return ChatOpenAI(
            model="planforge-gateway",
            api_key="planforge-gateway-no-key",
            base_url=f"{cfg.gateway_url}/v1",
            temperature=0,
        )

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extract JSON object from LLM response, tolerant of markdown fences."""
        import json

        # Strip markdown fences
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # If pure JSON failed, try extracting first {...} block
            import re
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            logger.error("Failed to parse JSON from LLM response: %s", text[:200])
            return {}

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert request into a filesystem-safe name."""
        import re
        name = re.sub(r"[^a-zA-Z0-9\s]", "", text.lower())
        name = re.sub(r"\s+", "_", name).strip("_")
        return name[:50] or "plan"
