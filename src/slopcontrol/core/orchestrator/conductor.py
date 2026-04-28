"""Central Conductor — the master agent that orchestrates plan execution."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from slopcontrol.core.domain_base.agent_factory import create_domain_agent
from slopcontrol.core.domain_base.plugin import DomainPlugin
from slopcontrol.core.knowledge.retriever import KnowledgeRetriever
from slopcontrol.core.plan.schema import DesignPlan

from .competition import CandidateConfig, CompetitionManager
from .cost_tracker import CostTracker
from .dispatch import DispatchEngine, OrchestrationError
from .handoff import HandoffProtocol
from .judge import CompetitionJudge
from .protocol import AgentType, StepStatus
from .registry import PluginRegistry
from .state import OrchestrationState
from .truth_db import TruthDB, TruthRecord

logger = logging.getLogger(__name__)


class Conductor:
    """Top-level orchestrator for SlopControl.

    Loads a :class:`DesignPlan`, identifies the required domain agents,
    executes each implementation step in order, manages cross-domain
    handoffs, runs verification, and persists results.
    """

    def __init__(
        self,
        registry: PluginRegistry | None = None,
        kb: KnowledgeRetriever | None = None,
        budget: float = 5.0,
        compete: bool = False,
        compete_agents: list[str] | None = None,
        compete_judge: str = "hybrid",
    ) -> None:
        self.registry = registry or PluginRegistry()
        if not self.registry.list_domains():
            self.registry.auto_discover()
        self.dispatch = DispatchEngine(self.registry)
        self.kb = kb
        self.state: OrchestrationState | None = None
        self.cost_tracker = CostTracker(daily_budget=budget)
        self.cost_tracker.load_history()
        self.compete = compete
        self.compete_agents = compete_agents
        self.compete_judge = compete_judge
        self.competition = CompetitionManager(self.registry)
        self.judge = CompetitionJudge(strategy=compete_judge)
        self.truth_db = TruthDB(kb=kb)

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

    def _execute_step(self, idx: int, step: dict[str, Any]) -> None:
        state = self.state
        assert state is not None
        state.mark_step(idx, StepStatus.IN_PROGRESS)

        domain_name, agent_type = self.dispatch.select_agent(step, state.plan)

        # -- Competition mode --------------------------------------------
        if self.compete or step.get("compete", False):
            self._execute_step_compete(idx, step, domain_name)
        else:
            # -- Sequential mode (legacy) --------------------------------
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

    def _execute_step_compete(self, idx: int, step: dict[str, Any], domain_name: str) -> None:
        """Run multiple candidates in parallel and pick a winner."""
        state = self.state
        assert state is not None

        # Build candidate list
        agent_names = step.get("compete_agents") or self.compete_agents
        if not agent_names:
            # Default: domain agent + opencode
            agent_names = [domain_name, "opencode"]

        candidates: list[CandidateConfig] = []
        for name in agent_names:
            if name == domain_name or self.registry.has(name):
                candidates.append(CandidateConfig(agent_name=name, model_spec=None))
            elif self.registry.get_external_adapter(name):
                candidates.append(CandidateConfig(agent_name=name, model_spec=None))
            else:
                logger.warning("Skipping unknown candidate '%s'", name)

        if not candidates:
            logger.warning("No valid candidates — falling back to sequential")
            return self._execute_step(idx, step)  # type: ignore[arg-type]

        # Budget gate
        estimated_cost = len(candidates) * step.get("estimated_cost", 0.01)
        if not self.cost_tracker.can_afford(estimated_cost):
            logger.warning("Budget exhausted — running cheapest candidate only")
            candidates = candidates[:1]

        # Run competition
        logger.info("Starting competition for step %d with %d candidates", idx, len(candidates))
        outcome = self.competition.compete(
            step=step,
            plan=state.plan,
            project_dir=state.project_dir,
            candidates=candidates,
            cost_tracker=self.cost_tracker,
        )

        # Judge
        winner = self.judge.judge(outcome)

        if winner is None:
            logger.error("All candidates failed for step %d", idx)
            state.record_error(idx, "All competition candidates failed")
            return

        # Promote winner
        self._promote_winner(winner, state.project_dir)

        # Record truth
        for cand in outcome.candidates:
            self.truth_db.record(
                TruthRecord(
                    task_type=cand.workspace.name if cand.workspace else "unknown",
                    agent=cand.agent_name,
                    model=cand.model_spec or "gateway",
                    pass_rate=cand.pass_rate,
                    cost_usd=cand.cost_usd,
                    duration=cand.duration,
                    domain=state.plan.domain,
                    plan_name=state.plan.name,
                    step_index=idx,
                    timestamp=datetime.now().isoformat(),
                )
            )

        state.record_artifact(
            path=str(state.project_dir / ".slopcontrol" / "competition" / f"step_{idx:03d}" / winner.agent_name),
            type="competition_winner",
            description=f"Step {idx + 1} winner: {winner.agent_name}",
        )

    def _promote_winner(self, winner: Any, project_dir: Path) -> None:
        """Copy winning workspace back to the main project."""
        import shutil

        winner_dir = winner.workspace
        if not winner_dir or not winner_dir.exists():
            logger.warning("Winner workspace missing — nothing to promote")
            return

        # Copy changed files from winner workspace into project
        for item in winner_dir.rglob("*"):
            if item.is_dir():
                continue
            rel = item.relative_to(winner_dir)
            dest = project_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)
            logger.debug("Promoted %s -> %s", item, dest)

        logger.info("Promoted winner workspace from %s", winner_dir)

    def _run_internal_step(
        self,
        idx: int,
        step: dict[str, Any],
        plugin: DomainPlugin,
    ) -> None:
        """Run one step using a SlopControl domain agent."""
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
        from slopcontrol.core.knowledge.ingest import KnowledgeIngest
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
