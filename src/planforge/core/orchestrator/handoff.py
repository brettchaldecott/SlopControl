"""Cross-domain handoff protocol — artifact creation and consumption."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from planforge.core.domain_base.session import DomainSession

from .protocol import HandoffArtifact
from .state import OrchestrationState


class HandoffProtocol:
    """Manages deliverables passed from one domain agent to another.

    Handoff artifacts are stored both in :class:`OrchestrationState`
    and ingested into the knowledge base so that future agents can
    retrieve them via semantic search.
    """

    def __init__(self, state: OrchestrationState) -> None:
        self.state = state

    # -- Creation -------------------------------------------------------

    def create(
        self,
        source_domain: str,
        target_domain: str,
        deliverable_type: str,
        description: str = "",
        context: dict[str, Any] | None = None,
    ) -> HandoffArtifact:
        """Register a new handoff artifact."""
        artifact = HandoffArtifact(
            id=str(uuid.uuid4())[:8],
            source_domain=source_domain,
            target_domain=target_domain,
            step_index=self.state.current_step,
            deliverable_type=deliverable_type,
            description=description,
            context=context or {},
        )
        self.state.handoffs.append(artifact)
        return artifact

    # -- Retrieval ------------------------------------------------------

    def pending_for(self, domain: str) -> list[HandoffArtifact]:
        """Return all un-retrieved artifacts targeting *domain*."""
        return [
            h for h in self.state.handoffs
            if h.target_domain == domain and not h.retrieved
        ]

    def mark_retrieved(self, artifact_id: str) -> None:
        """Mark an artifact as consumed."""
        for h in self.state.handoffs:
            if h.id == artifact_id:
                h.retrieved = True
                break

    # -- Materialisation -----------------------------------------------

    def to_markdown(self, artifact: HandoffArtifact) -> str:
        """Serialise a handoff so it can be ingested into the KB."""
        lines = [
            "---",
            f"id: {artifact.id}",
            f"source: {artifact.source_domain}",
            f"target: {artifact.target_domain}",
            f"type: {artifact.deliverable_type}",
            f"step: {artifact.step_index}",
            f"created: {artifact.created}",
            "---",
            "",
            f"# Handoff: {artifact.description or artifact.deliverable_type}",
            "",
            "## Context",
        ]
        for k, v in artifact.context.items():
            lines.append(f"- **{k}**: {v}")
        return "\n".join(lines)

    def save_to_disk(
        self,
        artifact: HandoffArtifact,
        project_dir: Path,
    ) -> Path:
        """Write a markdown handoff file under ``.planforge/handoffs/``."""
        handoffs_dir = project_dir / ".planforge" / "handoffs"
        handoffs_dir.mkdir(parents=True, exist_ok=True)
        outfile = handoffs_dir / f"handoff_{artifact.id}_{artifact.target_domain}.md"
        outfile.write_text(self.to_markdown(artifact))
        return outfile

    # -- Injection ------------------------------------------------------

    def inject_into_session(
        self,
        artifact: HandoffArtifact,
        session: DomainSession,
    ) -> None:
        """Push handoff context into an active domain session.

        Currently serialised as a system message; subclasses may
        override to write files, set env vars, etc.
        """
        context_text = self.to_markdown(artifact)
        # Store in session history as a system message
        session.record_turn(role="system", content=context_text)
        self.mark_retrieved(artifact.id)
