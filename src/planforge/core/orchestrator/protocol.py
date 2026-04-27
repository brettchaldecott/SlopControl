"""Shared constants and data structures for the orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    """Lifecycle states for an implementation step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentType(str, Enum):
    """Classification of an agent in the orchestrator."""

    INTERNAL_DOMAIN = "internal_domain"
    EXTERNAL_ADAPTER = "external_adapter"
    CONDUCTOR = "conductor"


@dataclass
class HandoffArtifact:
    """Cross-domain deliverable produced by one agent and consumed by another."""

    id: str                        # UUID
    source_domain: str             # e.g. "cad"
    target_domain: str             # e.g. "code"
    step_index: int                # Which plan step produced this
    deliverable_type: str          # e.g. "geometry-spec", "api-contract"
    description: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    retrieved: bool = False          # Has the target agent picked this up?

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "step_index": self.step_index,
            "deliverable_type": self.deliverable_type,
            "description": self.description,
            "context": self.context,
            "created": self.created,
            "retrieved": self.retrieved,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HandoffArtifact":
        return cls(
            id=data["id"],
            source_domain=data["source_domain"],
            target_domain=data["target_domain"],
            step_index=data["step_index"],
            deliverable_type=data["deliverable_type"],
            description=data.get("description", ""),
            context=data.get("context", {}),
            created=data.get("created", datetime.now().isoformat()),
            retrieved=data.get("retrieved", False),
        )
