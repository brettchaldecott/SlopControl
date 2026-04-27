"""Central Conductor — the master agent that orchestrates plan execution."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from planforge.core.domain_base.agent_factory import create_domain_agent
from planforge.core.domain_base.plugin import DomainPlugin
from planforge.core.knowledge.retriever import KnowledgeRetriever
from planforge.core.plan.schema import DesignPlan

from .dispatch import DispatchEngine, OrchestrationError
from .handoff import HandoffProtocol
from .protocol import AgentType, StepStatus
from .registry import PluginRegistry
from .state import OrchestrationState

logger = logging.getLogger(__name__)


class Conductor:
    """Top-level orchestrator for PlanForge.

    Loads a :class:`DesignPlan`, identifies the required domain agents,
    executes each implementation step in order, manages cross-domain
    handoffs, runs verification, and persists results.
    """

    def __init__(
        self,
        registry: PluginRegistry | None = None,
        kb: KnowledgeRetriever | None = None,
    ) -> None:
        self.registry = registry or PluginRegistry()
        if not self.registry.list_domains():
            self.registry.auto_discover()
        self.dispatch = DispatchEngine(self.registry)
        self.kb = kb
        self.state: OrchestrationState | None = None

    # -- Main entry point -----------------------------------------------

    def run_plan(
        self,
        plan: DesignPlan,
        project_dir: Path | str,
    ) -> dict[str, Any]:
        """Execute *plan* top-down.

        Returns:
            Dict with ``success``, ``artifacts``, ``handoffs``,
            ``verification_results``, ``errors``.
        """
        project_dir = Path(project_dir)
        self.state = OrchestrationState(plan=plan, project_dir=project_dir)

        # Phase 1: Scaffold
        self._scaffold()

        # Phase 2: Dispatch implementation steps
        for idx, step in enumerate(plan.implementation_steps):
            self.state.current_step = idx
            try:
                self._execute_step(idx, step)
            except Exception as exc:
                logger.exception("Step %d failed", idx)
                self.state.mark_step(idx, StepStatus.FAILED)
                self.state.record_error(idx, str(exc))

        # Phase 3: Verify
        self._verify()

        # Phase 4: Persist
        self._persist()

        return {
            "success": all(
                s in (StepStatus.COMPLETED, StepStatus.SKIPPED)
                for s in self.state.step_states
            ),
            "artifacts": self.state.artifacts,
            "handoffs": [h.to_dict() for h in self.state.handoffs],
            "verification_results": [
                {"check": r.check, "passed": r.passed, "message": r.message}
                for r in self.state.verification_results
            ],
            "errors": self.state.error_log,
        }

    # -- Phase 1: Scaffold ----------------------------------------------

    def _scaffold(self) -> None:
        state = self.state
        assert state is not None
        plugin = self.registry.get(state.plan.domain)
        plugin.scaffold_project(state.project_dir)
        # Also scaffold for any cross-domain steps
        for step in state.plan.implementation_steps:
            domain = step.get("domain") or state.plan.domain
            if self.registry.has(domain):
                self.registry.get(domain).scaffold_project(state.project_dir)

    # -- Phase 2: Dispatch steps ----------------------------------------

    def _execute_step(self, idx: int, step: dict[str, Any]) -> None:
        state = self.state
        assert state is not None
        state.mark_step(idx, StepStatus.IN_PROGRESS)

        domain_name, agent_type = self.dispatch.select_agent(step, state.plan)

        if agent_type == AgentType.INTERNAL_DOMAIN:
            plugin = self.registry.get(domain_name)
            self._run_internal_step(idx, step, plugin)
        elif agent_type == AgentType.EXTERNAL_ADAPTER:
            adapter = self.registry.get_external_adapter(domain_name)
            if adapter is None:
                raise OrchestrationError(f"External adapter '{domain_name}' not found")
            self._run_external_step(idx, step, adapter)
        else:
            raise OrchestrationError(f"Unsupported agent type: {agent_type}")

        state.mark_step(idx, StepStatus.COMPLETED)

    def _run_internal_step(
        self,
        idx: int,
        step: dict[str, Any],
        plugin: DomainPlugin,
    ) -> None:
        """Run one step using a PlanForge domain agent."""
        state = self.state
        assert state is not None

        # Build domain agent
        agent = create_domain_agent(
            plugin=plugin,
            project_dir=state.project_dir,
        )

        # Compose prompt with KB context if available
        prompt = f"Implement step {idx + 1}: {step.get('description', '')}"
        if self.kb:
            kb_context = self.kb.get_context_string(query=prompt, k=3)
            if kb_context:
                prompt = f"Context:\n{kb_context}\n\n{prompt}"

        result = agent.invoke({"messages": [("user", prompt)]})
        content = str(result)
        logger.info("Step %d result: %s", idx, content[:200])

        # Record artifact if produced
        artifact_path = step.get("artifact_path")
        if artifact_path:
            state.record_artifact(
                path=str(state.project_dir / artifact_path),
                type="step_output",
                description=f"Step {idx + 1} output",
            )

        # Ingest step result into KB
        if self.kb:
            self._ingest_step_result(idx, content)

    def _run_external_step(
        self,
        idx: int,
        step: dict[str, Any],
        adapter: Any,
    ) -> None:
        """Run one step using an external agent adapter (OpenCode, Claude, Cursor)."""
        state = self.state
        assert state is not None
        task = step.get("description", "")
        result = adapter.execute(task=task, context_dir=state.project_dir)
        logger.info("External step %d: success=%s", idx, result.get("success"))
        if not result.get("success"):
            raise OrchestrationError(result.get("stderr", "External agent failed"))

    # -- Phase 3: Verify ------------------------------------------------

    def _verify(self) -> None:
        state = self.state
        assert state is not None
        domain_name = state.plan.domain
        if not self.registry.has(domain_name):
            logger.warning("No verifier for domain '%s'", domain_name)
            return

        verifiers = self.registry.get(domain_name).get_verifiers()
        for verifier in verifiers:
            try:
                results = verifier.validate(str(state.project_dir))
                state.verification_results.extend(results)
            except Exception as exc:
                logger.warning("Verifier %s failed: %s", verifier.__class__.__name__, exc)

    # -- Phase 4: Persist -----------------------------------------------

    def _persist(self) -> None:
        state = self.state
        assert state is not None
        from . import persistence
        persistence.save(state, state.project_dir)
        logger.info("Orchestration complete — state saved.")

    # -- Knowledge helpers -----------------------------------------------

    def _ingest_step_result(self, idx: int, content: str) -> None:
        if self.kb is None:
            return
        from planforge.core.knowledge.ingest import KnowledgeIngest
        ingest = KnowledgeIngest(backend=self.kb.backend)
        text = f"# Step {idx + 1} Result\n\n{content}"
        ingest.index_note(source=f"step:{idx}", text=text, metadata={"type": "step_result"})

    # -- Handoff helpers (for future expansion) -------------------------

    def create_handoff(
        self,
        source: str,
        target: str,
        deliverable_type: str,
        description: str = "",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Manually create a cross-domain handoff.

        Typically called from an agent callback or after a step
        that produces data another domain needs.
        """
        state = self.state
        assert state is not None
        protocol = HandoffProtocol(state)
        artifact = protocol.create(source, target, deliverable_type, description, context)
        protocol.save_to_disk(artifact, state.project_dir)
        if self.kb:
            self.kb.ingest_note(source=f"handoff:{artifact.id}", text=protocol.to_markdown(artifact))
