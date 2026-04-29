"""ImplementationObserver - closes the loop between execution and planning.

After the Conductor runs steps and verification, this observer:
1. Analyzes test, type check, and coverage results
2. Records empirical truths in TruthDB
3. Generates insights that can be fed back into future planning sessions
4. Indexes observations into the Knowledge Base with RAPTOR
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from slopcontrol.core.orchestrator.truth_db import TruthDB, TruthRecord
from slopcontrol.core.knowledge.retriever import KnowledgeRetriever
from slopcontrol.core.knowledge.indexer import KnowledgeIndexer
from slopcontrol.core.verify.base import VerificationResult

logger = logging.getLogger(__name__)


@dataclass
class ImplementationObservation:
    """Structured observation from an implementation run."""
    plan_name: str
    step_index: int
    verification_results: list[VerificationResult]
    truths_recorded: int = 0
    insights: list[str] = None  # type: ignore
    success: bool = False

    def __post_init__(self) -> None:
        if self.insights is None:
            self.insights = []


class ImplementationObserver:
    """Observes implementation outcomes and feeds them back into the system."""

    def __init__(
        self,
        truth_db: TruthDB | None = None,
        indexer: KnowledgeIndexer | None = None,
        retriever: KnowledgeRetriever | None = None,
    ) -> None:
        self.truth_db = truth_db
        self.indexer = indexer
        self.retriever = retriever

    def observe(
        self,
        project_dir: Path,
        plan_name: str,
        step_index: int,
        verification_results: list[VerificationResult],
        cost_usd: float = 0.0,
        duration: float = 0.0,
    ) -> ImplementationObservation:
        """Analyze results from one implementation step and record truths."""
        obs = ImplementationObservation(
            plan_name=plan_name,
            step_index=step_index,
            verification_results=verification_results,
        )

        passed = sum(1 for r in verification_results if r.passed)
        total = len(verification_results) or 1
        pass_rate = passed / total

        obs.success = pass_rate >= 0.8  # arbitrary high bar for "good"

        # Record empirical truth
        if self.truth_db:
            record = TruthRecord(
                task_type=f"step_{step_index}",
                agent="slopcontrol",
                model="grok:grok-3-beta",  # current default
                pass_rate=pass_rate,
                cost_usd=cost_usd,
                duration=duration,
                domain="code",
                plan_name=plan_name,
                step_index=step_index,
                timestamp="",
            )
            self.truth_db.record(record)
            obs.truths_recorded += 1

        # Generate insights from failures
        failures = [r for r in verification_results if not r.passed]
        for failure in failures[:3]:  # limit noise
            obs.insights.append(
                f"Step {step_index}: {failure.check} failed - {failure.message}"
            )

        # Index observation into knowledge base
        self._index_observation(obs, project_dir)

        logger.info(
            "Observed step %d of %s: pass_rate=%.2f, truths=%d",
            step_index, plan_name, pass_rate, obs.truths_recorded
        )
        return obs

    def _index_observation(self, obs: ImplementationObservation, project_dir: Path) -> None:
        """Index the observation so future planning sessions can learn from it."""
        if not self.indexer:
            return

        text = f"# Implementation Observation\n\n"
        text += f"Plan: {obs.plan_name}\n"
        text += f"Step: {obs.step_index}\n"
        text += f"Success: {obs.success}\n\n"

        if obs.insights:
            text += "## Insights\n\n"
            for insight in obs.insights:
                text += f"- {insight}\n"

        try:
            self.indexer.index_text(
                text=text,
                source=f"observation:{obs.plan_name}:step{obs.step_index}"
            )
        except Exception as e:
            logger.debug("Failed to index observation: %s", e)

    def get_lessons_for_planning(self, query: str = "best practices from past implementations") -> str:
        """Return learned lessons that can be injected into planning prompts."""
        if not self.retriever:
            return ""
        try:
            return self.retriever.get_context_string(query=query, k=5, include_summaries=True)
        except Exception:
            return ""