"""Orchestration state — the conductor's working memory for a plan run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from planforge.core.plan.schema import DesignPlan
from planforge.core.verify.base import VerificationResult

from .protocol import HandoffArtifact, StepStatus


@dataclass
class OrchestrationState:
    """Mutable working state for a single :meth:`Conductor.run_plan` execution."""

    plan: DesignPlan
    project_dir: Path
    step_states: list[StepStatus] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    handoffs: list[HandoffArtifact] = field(default_factory=list)
    verification_results: list[VerificationResult] = field(default_factory=list)
    current_step: int = 0
    error_log: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def mark_step(self, index: int, status: StepStatus) -> None:
        """Update the status of step *index*."""
        while len(self.step_states) <= index:
            self.step_states.append(StepStatus.PENDING)
        self.step_states[index] = status

    def record_artifact(self, path: str, type: str, description: str = "") -> None:
        self.artifacts.append({
            "path": path,
            "type": type,
            "description": description,
            "step": self.current_step,
        })

    def record_error(self, step: int, message: str) -> None:
        self.error_log.append({"step": step, "message": message})

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_name": self.plan.name,
            "plan_domain": self.plan.domain,
            "plan_version": self.plan.version,
            "project_dir": str(self.project_dir),
            "current_step": self.current_step,
            "step_states": [s.value for s in self.step_states],
            "artifacts": self.artifacts,
            "handoffs": [h.to_dict() for h in self.handoffs],
            "verification_results": [
                {
                    "check": r.check,
                    "passed": r.passed,
                    "message": r.message,
                    "severity": r.severity,
                }
                for r in self.verification_results
            ],
            "error_log": self.error_log,
            "metadata": self.metadata,
        }
