"""Competition manager for parallel candidate execution.

For a single plan step, runs multiple agents (internal or external) in
isolated workspaces, collects verifiable results, and lets the judge pick
a winner.
"""

from __future__ import annotations

import logging
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from slopcontrol.core.domain_base.agent_factory import create_domain_agent
from slopcontrol.core.domain_base.plugin import DomainPlugin
from slopcontrol.core.orchestrator.dispatch import OrchestrationError
from slopcontrol.core.verify.base import VerificationResult

from .registry import PluginRegistry

logger = logging.getLogger(__name__)


@dataclass
class CandidateConfig:
    """How to instantiate one competing candidate."""

    agent_name: str          # "slopcontrol", "opencode", etc.
    model_spec: str | None   # e.g. "grok:grok-3-beta" or None for "gateway"
    workspace_mode: str = "clone"  # "clone" | "scratch"


@dataclass
class CandidateResult:
    """Outcome of a single candidate run."""

    agent_name: str
    model_spec: str | None
    verifier_results: list[VerificationResult]
    pass_rate: float = 0.0
    artifact_paths: list[Path] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    workspace: Path = field(default_factory=lambda: Path("."))
    cost_usd: float = 0.0

    @property
    def passed(self) -> bool:
        return self.pass_rate >= 1.0


@dataclass
class CompetitionOutcome:
    """Result of a full competition round."""

    candidates: list[CandidateResult]
    winner: CandidateResult | None = None
    step_index: int = 0
    duration_total: float = 0.0


class CompetitionManager:
    """Manages parallel execution of competing agents for a plan step."""

    def __init__(
        self,
        registry: PluginRegistry,
        max_workers: int = 3,
        step_timeout: float = 300.0,
    ) -> None:
        self.registry = registry
        self.max_workers = max_workers
        self.step_timeout = step_timeout

    # -- Public API -----------------------------------------------------

    def compete(
        self,
        step: dict[str, Any],
        plan: Any,
        project_dir: Path,
        candidates: list[CandidateConfig],
        cost_tracker: Any | None = None,
    ) -> CompetitionOutcome:
        """Run every *candidate* in parallel, score, return winner."""
        start = datetime.now()
        workspaces = self._prepare_workspaces(
            project_dir, candidates, step_index=plan.current_step if hasattr(plan, "current_step") else 0
        )

        results: list[CandidateResult] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._run_candidate,
                    cfg,
                    step,
                    plan,
                    workspaces[cfg],
                    cost_tracker,
                ): cfg
                for cfg in candidates
            }

            for future in as_completed(futures):
                cfg = futures[future]
                try:
                    result = future.result(timeout=self.step_timeout)
                    results.append(result)
                except Exception as exc:
                    logger.exception("Candidate %s failed", cfg.agent_name)
                    results.append(
                        CandidateResult(
                            agent_name=cfg.agent_name,
                            model_spec=cfg.model_spec,
                            verifier_results=[],
                            pass_rate=0.0,
                            stderr=str(exc),
                        )
                    )

        # Clean up all losing workspaces (keep winner + failed for inspection)
        # (done by caller after promoting winner)

        elapsed = (datetime.now() - start).total_seconds()
        return CompetitionOutcome(
            candidates=results,
            step_index=getattr(plan, "current_step", 0),
            duration_total=elapsed,
        )

    # -- Internal -------------------------------------------------------

    def _prepare_workspaces(
        self,
        project_dir: Path,
        candidates: list[CandidateConfig],
        step_index: int,
    ) -> dict[CandidateConfig, Path]:
        """Create isolated temp directories per candidate."""
        base = project_dir / ".slopcontrol" / "competition" / f"step_{step_index:03d}"
        if base.exists():
            shutil.rmtree(base)

        workspaces: dict[CandidateConfig, Path] = {}
        for cfg in candidates:
            ws = base / cfg.agent_name
            ws.mkdir(parents=True, exist_ok=True)
            if cfg.workspace_mode == "clone" and project_dir.exists():
                # Shallow copy of project files (skip .slopcontrol, .git, etc.)
                self._shallow_clone(project_dir, ws)
            workspaces[cfg] = ws

        return workspaces

    def _shallow_clone(self, source: Path, dest: Path) -> None:
        """Copy project files, skipping heavy/secret directories."""
        ignore = {".slopcontrol", ".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", ".env"}
        for item in source.iterdir():
            if item.name in ignore:
                continue
            if item.is_dir():
                shutil.copytree(item, dest / item.name, ignore=lambda *_: {*ignore}, dirs_exist_ok=True)
            elif item.is_file():
                shutil.copy2(item, dest / item.name)

    def _run_candidate(
        self,
        cfg: CandidateConfig,
        step: dict[str, Any],
        plan: Any,
        workspace: Path,
        cost_tracker: Any | None,
    ) -> CandidateResult:
        """Run one candidate in its workspace."""
        start = datetime.now()
        agent_type = self._classify_agent(cfg.agent_name)

        # Dispatch
        if agent_type == "internal_domain":
            artifacts, verifier_results = self._run_internal(
                cfg, step, plan, workspace
            )
        elif agent_type == "external_adapter":
            artifacts, verifier_results = self._run_external(
                cfg, step, workspace
            )
        else:
            raise ValueError(f"Unknown agent type for {cfg.agent_name}")

        duration = (datetime.now() - start).total_seconds()

        # Compute pass rate
        if verifier_results:
            passed = sum(1 for r in verifier_results if r.passed)
            pass_rate = passed / len(verifier_results)
        else:
            pass_rate = 0.0

        # Estimate cost (placeholder — real implementation tracks tokens)
        cost = self._estimate_cost(cfg, step, duration)
        if cost_tracker:
            cost_tracker.record(
                task_type=step.get("task_type", "unknown"),
                provider=cfg.model_spec or cfg.agent_name,
                model=cfg.model_spec or "unknown",
                cost_usd=cost,
                step_index=plan.current_step if hasattr(plan, "current_step") else 0,
                plan_name=getattr(plan, "name", "unnamed"),
            )

        return CandidateResult(
            agent_name=cfg.agent_name,
            model_spec=cfg.model_spec,
            verifier_results=verifier_results,
            pass_rate=pass_rate,
            artifact_paths=artifacts,
            duration=duration,
            workspace=workspace,
            cost_usd=cost,
        )

    def _classify_agent(self, name: str) -> str:
        if self.registry.has(name):
            return "internal_domain"
        if self.registry.get_external_adapter(name):
            return "external_adapter"
        raise OrchestrationError(f"Unknown agent: {name}")

    def _run_internal(
        self,
        cfg: CandidateConfig,
        step: dict[str, Any],
        plan: Any,
        workspace: Path,
    ) -> tuple[list[Path], list[VerificationResult]]:
        """Run an internal domain agent."""
        plugin = self.registry.get(cfg.agent_name)
        agent = create_domain_agent(
            plugin=plugin,
            project_dir=workspace,
            model=self._resolve_model(cfg.model_spec),
        )
        prompt = f"Implement step: {step.get('description', '')}"
        agent.invoke({"messages": [("user", prompt)]})

        # Collect artifacts (anything written to workspace)
        artifacts = list(workspace.rglob("*"))
        artifacts = [p for p in artifacts if p.is_file()]

        # Run verifiers on workspace
        verifier_results: list[VerificationResult] = []
        for verifier in plugin.get_verifiers():
            try:
                verifier_results.extend(verifier.validate(str(workspace)))
            except Exception as exc:
                logger.warning("Verifier %s failed: %s", verifier.__class__.__name__, exc)

        return artifacts, verifier_results

    def _run_external(
        self,
        cfg: CandidateConfig,
        step: dict[str, Any],
        workspace: Path,
    ) -> tuple[list[Path], list[VerificationResult]]:
        """Run an external agent adapter (OpenCode)."""
        adapter = self.registry.get_external_adapter(cfg.agent_name)
        assert adapter is not None
        result = adapter.execute(task=step.get("description", ""), context_dir=workspace)

        artifacts = []
        # If the adapter wrote to the workspace, collect files
        artifacts = list(workspace.rglob("*"))
        artifacts = [p for p in artifacts if p.is_file()]

        verifier_results: list[VerificationResult] = []
        # External adapters don't have verifiers natively;
        # we rely on the domain verifiers to run afterward.
        return artifacts, verifier_results

    def _resolve_model(self, model_spec: str | None) -> Any:
        """Convert a model spec (e.g. 'grok:grok-3-beta') into a LangChain model."""
        from slopcontrol.core.providers.registry import get_model
        if model_spec is None:
            return get_model()
        return get_model(model_spec)

    def _estimate_cost(self, cfg: CandidateConfig, step: dict[str, Any], duration: float) -> float:
        """Very rough cost heuristic.  Real implementation uses token counting."""
        # USD per minute of compute (proxy for LLM cost)
        base_rate: dict[str, float] = {
            "grok": 0.003,
            "openai": 0.005,
            "ollama": 0.0001,
            "opencode": 0.005,
        }
        # Extract provider from model_spec
        if cfg.model_spec and ":" in cfg.model_spec:
            provider = cfg.model_spec.split(":")[0].lower()
        else:
            provider = cfg.agent_name.lower()
        rate = base_rate.get(provider, 0.005)
        return round(duration / 60.0 * rate, 6)
