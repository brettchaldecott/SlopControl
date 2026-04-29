"""Interactive PlanningSession - rich multi-turn conversational planner.

This replaces the limited CLI _interactive_plan() with a stateful session
that supports natural discussion, iterative refinement, and clear finalization.
It integrates with the Knowledge Base and will later connect to the Conductor.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from slopcontrol.core.knowledge.retriever import KnowledgeRetriever
from slopcontrol.core.plan.generator import PlanGenerator
from slopcontrol.core.plan.renderer import read_plan, render_plan
from slopcontrol.core.plan.schema import DesignPlan

from .prompts import PLANNING_SYSTEM_PROMPT, REFINEMENT_PROMPT, FINALIZE_PROMPT, LEARNING_PROMPT

logger = logging.getLogger(__name__)


class PlanningState(str, Enum):
    EXPLORATION = "exploration"
    DRAFTING = "drafting"
    REFINEMENT = "refinement"
    FINALIZED = "finalized"
    IMPLEMENTATION = "implementation"


@dataclass
class PlanningSession:
    """Stateful interactive planning session."""

    project_dir: Path
    retriever: KnowledgeRetriever | None = None
    model: BaseChatModel | None = None
    state: PlanningState = PlanningState.EXPLORATION
    plan: DesignPlan | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    session_id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = f"plan_{self.project_dir.name}_{hash(str(self.project_dir)) % 10000:04d}"

        if self.model is None:
            from slopcontrol.core.providers.registry import get_model
            self.model = get_model()  # uses gateway with Grok-first config

    def run_conversation(self, initial_request: str | None = None) -> None:
        """Run the main interactive planning loop.

        This is the rich multi-turn experience the user requested.
        """
        console = self._get_console()

        console.print("\n[bold cyan]SlopControl Interactive Planning Session[/bold cyan]")
        console.print("We will iterate together until the plan is ready for implementation.\n")

        if not initial_request:
            initial_request = console.input("[bold]What would you like to build? [/bold]")

        self.history.append({"role": "user", "content": initial_request})

        # Phase 1: Exploration & initial draft
        self._perform_exploration(initial_request)

        # Main refinement loop
        while self.state in (PlanningState.DRAFTING, PlanningState.REFINEMENT):
            self._show_current_plan()
            feedback = console.input(
                "\n[bold]Your thoughts or changes? [/bold](type 'finalize' when ready, or 'show' to see plan) "
            ).strip()

            if not feedback:
                continue

            self.history.append({"role": "user", "content": feedback})

            if feedback.lower() in ("finalize", "finalise", "done", "implement"):
                self._finalize_plan()
                break
            elif feedback.lower() in ("show", "plan"):
                continue
            else:
                self._refine_plan(feedback)

        if self.state == PlanningState.FINALIZED:
            self._save_and_index()
            console.print("\n[bold green]Plan finalized and indexed.[/bold green]")
            console.print("Run `slopcontrol orchestrate` to begin implementation.")

    def _perform_exploration(self, request: str) -> None:
        """Generate initial plan draft using knowledge context."""
        from rich.console import Console
        console = Console()

        kb_context = ""
        if self.retriever:
            try:
                kb_context = self.retriever.get_context_string(query=request, k=4)
                if kb_context:
                    console.print("[dim]Loaded relevant knowledge from previous projects.[/dim]")
            except Exception as e:
                logger.debug("KB context unavailable: %s", e)

        generator = PlanGenerator(model=self.model, retriever=self.retriever)
        self.plan = generator.generate(
            request=request,
            domain="code",
            name=self.project_dir.name,
            agents=["slopcontrol"]
        )
        self.state = PlanningState.DRAFTING
        console.print("[green]Initial plan drafted from your request.[/green]")

    def _show_current_plan(self) -> None:
        """Display current plan state."""
        if not self.plan:
            return
        from rich.console import Console
        console = Console()
        console.print("\n[bold]Current Plan:[/bold]")
        console.print(f"Name: {self.plan.name}")
        console.print(f"Status: {self.plan.status} (v{self.plan.version})")
        console.print(f"Requirements: {len(self.plan.requirements)}")
        console.print(f"Decisions: {len(self.plan.decisions)}")
        console.print(f"Steps: {len(self.plan.implementation_steps)}")

    def _refine_plan(self, feedback: str) -> None:
        """Use LLM to refine the current plan based on user feedback."""
        if not self.plan:
            return

        from rich.console import Console
        console = Console()

        kb_context = ""
        if self.retriever:
            try:
                kb_context = self.retriever.get_context_string(query=feedback, k=3)
            except Exception:
                pass

        prompt = REFINEMENT_PROMPT.format(
            current_plan=self._plan_to_text(),
            user_feedback=feedback,
            kb_context=kb_context or "(no additional context)",
        )

        response = self.model.invoke([SystemMessage(content=prompt)])
        content = response.content if isinstance(response.content, str) else str(response.content)

        # Use generator's modify which already handles LLM refinement
        generator = PlanGenerator(model=self.model, retriever=self.retriever)
        updated_plan = generator.modify(
            current_plan=self.plan,
            modification=feedback,
            retriever=self.retriever
        )
        self.plan = updated_plan
        self.state = PlanningState.REFINEMENT
        console.print("[green]Plan updated based on your feedback.[/green]")

    def _finalize_plan(self) -> None:
        """Mark plan as ready for implementation."""
        if not self.plan:
            return
        self.plan.status = "finalized"
        self.plan.version = "1.0"
        if "slopcontrol" not in self.plan.agents:
            self.plan.agents.append("slopcontrol")
        self.state = PlanningState.FINALIZED

    def _plan_to_text(self) -> str:
        """Convert current plan to readable text for prompts."""
        if not self.plan:
            return "No plan yet."
        from slopcontrol.core.plan.renderer import PlanRenderer
        renderer = PlanRenderer()
        return renderer.render(self.plan)

    def _save_and_index(self) -> None:
        """Save finalized plan and index it into knowledge base."""
        if not self.plan:
            return
        plan_path = self.project_dir / "slop_control.md"
        render_plan(self.plan, plan_path)

        if self.retriever and self.retriever.backend:
            try:
                from slopcontrol.core.knowledge.ingest import KnowledgeIngest
                ingest = KnowledgeIngest(backend=self.retriever.backend)
                ingest.index_note(
                    source=str(plan_path),
                    text=plan_path.read_text(),
                    metadata={"type": "finalized_plan", "session": self.session_id}
                )
                logger.info("Finalized plan indexed into knowledge base")
            except Exception as exc:
                logger.warning("Failed to index finalized plan: %s", exc)

    def _get_console(self):
        """Get rich console (avoid circular imports)."""
        from rich.console import Console
        return Console()