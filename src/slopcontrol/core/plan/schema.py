"""Plan schema – the datamodel for the ``slop_control.md`` artifact.

The plan is the primary artifact.  Code, configs, and
verification results are disposable products generated from it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DesignPlan:
    """Primary artifact for every SlopControl project.

    Rendered as ``slop_control.md`` with YAML frontmatter + structured
    body sections.  Append-only after initial creation.
    """

    # ── YAML frontmatter ─────────────────────────────────────────────
    name: str = ""
    domain: str = "code"            # "code" | "code"
    version: str = "1.0"
    status: str = "draft"          # draft | in_progress | verified | archived
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)

    # ── Body sections ─────────────────────────────────────────────────
    requirements: list[str] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    implementation_steps: list[dict[str, Any]] = field(default_factory=list)
    verification_log: list[dict[str, Any]] = field(default_factory=list)
    appendices: list[dict[str, Any]] = field(default_factory=list)

    # ── Extra metadata (not rendered) ───────────────────────────────
    _metadata: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_frontmatter(self) -> dict[str, Any]:
        """Return dict suitable for YAML frontmatter serialization."""
        return {
            "name": self.name,
            "domain": self.domain,
            "version": self.version,
            "status": self.status,
            "created": self.created,
            "tags": self.tags,
            "agents": self.agents,
        }

    @classmethod
    def from_frontmatter(cls, data: dict[str, Any]) -> "DesignPlan":
        """Reconstruct from parsed frontmatter dict."""
        return cls(
            name=data.get("name", ""),
            domain=data.get("domain", "code"),
            version=data.get("version", "1.0"),
            status=data.get("status", "draft"),
            created=data.get("created", datetime.now().isoformat()),
            tags=data.get("tags", []),
            agents=data.get("agents", []),
        )
