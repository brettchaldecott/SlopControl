"""Plan generator – LLM prompt that converts requirements into a DesignPlan.

Uses the local gateway and knowledge base for context.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from slopcontrol.core.gateway.config import GatewayConfig
from slopcontrol.core.gateway.fallback import create_fallback_chain
from slopcontrol.core.knowledge.retriever import KnowledgeRetriever

from .schema import DesignPlan

logger = logging.getLogger(__name__)

PLAN_GENERATION_PROMPT = """You are SlopControl's planning agent.
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

PLAN_MODIFICATION_PROMPT = """You are SlopControl's planning agent.
You need to modify an existing plan based on user feedback.

Current plan:
{current_plan}

Knowledge base context:
{kb_context}

Modification request: {modification}

Output the COMPLETE updated plan as valid JSON with:
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
        domain: str = "code",
        name: str = "",
        tags: list[str] | None = None,
        agents: list[str] | None = None,
    ) -> DesignPlan:
        """Generate a new DesignPlan from a user request.

        Gracefully handles missing retriever (KB unavailable).
        """
        # 1. Build KB context (including learned truths)
        kb_context = ""
        if self.retriever:
            try:
                kb_context = self.retriever.get_context_string(query=request, k=5)
                # Also pull historical lessons if TruthDB is available
                from slopcontrol.core.orchestrator.truth_db import TruthDB
                truth_db = TruthDB(retriever=self.retriever)
                lessons = truth_db.get_lessons(domain=domain, k=3)
                if lessons and "No historical" not in lessons:
                    kb_context = f"Historical lessons:\n{lessons}\n\n{kb_context}"
            except Exception as exc:  # KB may be in no-op fallback state
                logger.warning("Knowledge retriever unavailable: %s", exc)
                kb_context = "(knowledge base unavailable)"

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
            agents=agents or ["slopcontrol"],
            requirements=plan_dict.get("requirements", []),
            decisions=plan_dict.get("decisions", []),
            implementation_steps=plan_dict.get("implementation_steps", []),
            verification_log=plan_dict.get("verification_log", []),
        )

    def ask_clarifications(self, request: str, k: int = 3) -> list[str]:
        """Ask 2-3 clarifying questions about the user's request."""
        prompt = (
            "The user wants to build: " + request + "\n\n"
            "Ask 2-3 short clarifying questions to better understand their needs. "
            "Output ONLY a JSON array of strings:\n"
            '["question 1", "question 2", "question 3"]'
        )
        try:
            response = self.model.invoke([HumanMessage(content=prompt)])
            content = response.content if isinstance(response.content, str) else str(response.content)
            questions = self._extract_json(content)
            if isinstance(questions, list):
                return [q for q in questions if isinstance(q, str)][:3]
        except Exception as exc:
            logger.warning("Failed to generate clarifications: %s", exc)
        return []

    def modify(
        self,
        current_plan: DesignPlan,
        modification: str,
        retriever: "KnowledgeRetriever | None" = None,
    ) -> DesignPlan:
        """Modify an existing plan based on user feedback."""
        kb_context = ""
        if retriever or self.retriever:
            r = retriever or self.retriever
            try:
                kb_context = r.get_context_string(query=modification, k=2)
            except Exception as exc:  # KB may be in no-op fallback state
                logger.warning("Knowledge retriever unavailable during modify: %s", exc)
                kb_context = "(knowledge base unavailable)"

        # Serialize current plan for the prompt
        from dataclasses import asdict
        import json as _json
        current_json = _json.dumps(asdict(current_plan), indent=2, default=str)

        prompt = PLAN_MODIFICATION_PROMPT.format(
            current_plan=current_json,
            kb_context=kb_context or "(no knowledge base context available)",
            modification=modification,
        )

        response = self.model.invoke([SystemMessage(content=prompt)])
        content = response.content if isinstance(response.content, str) else str(response.content)

        plan_dict = self._extract_json(content)

        return DesignPlan(
            name=current_plan.name,
            domain=current_plan.domain,
            tags=current_plan.tags,
            agents=current_plan.agents,
            requirements=plan_dict.get("requirements", current_plan.requirements),
            decisions=plan_dict.get("decisions", current_plan.decisions),
            implementation_steps=plan_dict.get("implementation_steps", current_plan.implementation_steps),
            verification_log=plan_dict.get("verification_log", current_plan.verification_log),
        )

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def _default_model(self) -> BaseChatModel:
        """Create a default model via the gateway."""
        from langchain_openai import ChatOpenAI

        cfg = GatewayConfig.from_env()
        return ChatOpenAI(
            model="slopcontrol-gateway",
            api_key="slopcontrol-gateway-no-key",
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
