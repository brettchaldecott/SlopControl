"""Truth database — empirical performance records per (task, agent, model).

Uses the existing KnowledgeBase infrastructure (Qdrant / brute-force)
to store and retrieve verifier outcomes.  Over time this builds a
learned understanding of which agents excel at which task types.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from slopcontrol.core.knowledge.indexer import KnowledgeIndexer
from slopcontrol.core.knowledge.retriever import KnowledgeRetriever

logger = logging.getLogger(__name__)


@dataclass
class TruthRecord:
    task_type: str
    agent: str
    model: str
    pass_rate: float
    cost_usd: float
    duration: float
    domain: str
    plan_name: str
    step_index: int
    timestamp: str

    def to_markdown(self) -> str:
        return (
            f"## Performance Record\n\n"
            f"- **Task**: {self.task_type}\n"
            f"- **Agent**: {self.agent}\n"
            f"- **Model**: {self.model}\n"
            f"- **Pass Rate**: {self.pass_rate:.2%}\n"
            f"- **Cost**: ${self.cost_usd:.4f}\n"
            f"- **Duration**: {self.duration:.1f}s\n"
            f"- **Domain**: {self.domain}\n"
            f"- **Plan**: {self.plan_name} (step {self.step_index})\n"
            f"- **Timestamp**: {self.timestamp}\n"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type,
            "agent": self.agent,
            "model": self.model,
            "pass_rate": self.pass_rate,
            "cost_usd": self.cost_usd,
            "duration": self.duration,
            "domain": self.domain,
            "plan_name": self.plan_name,
            "step_index": self.step_index,
            "timestamp": self.timestamp,
        }


class TruthDB:
    """Interface to store and query empirical agent performance."""

    def __init__(
        self,
        indexer: KnowledgeIndexer | None = None,
        retriever: KnowledgeRetriever | None = None,
    ) -> None:
        self.indexer = indexer
        self.retriever = retriever

    # -- Recording -------------------------------------------------------

    def record(self, rec: TruthRecord) -> None:
        """Ingest a performance record into the knowledge base."""
        if self.indexer is None:
            logger.debug("No KB indexer connected — skipping truth record: %s", rec.agent)
            return
        try:
            self.indexer.index_text(
                text=rec.to_markdown(),
                source=f"truth:{rec.agent}:{rec.task_type}",
            )
            logger.debug("Recorded truth for %s/%s", rec.agent, rec.task_type)
        except Exception as exc:
            logger.warning("Failed to record truth record: %s", exc)

    # -- Global file mirror (human-browsable) -----------------------------

    def _append_to_global_file(self, rec: TruthRecord) -> Path | None:
        """Mirror the truth record to a file under ~/.slopcontrol/knowledge/ for browsing."""
        import os
        from pathlib import Path

        base = Path.home() / ".slopcontrol" / "knowledge" / "truth" / rec.domain
        try:
            base.mkdir(parents=True, exist_ok=True)
            from datetime import datetime

            month = datetime.now().strftime("%Y-%m")
            file_path = base / f"{month}_{rec.agent}_{rec.task_type.replace(' ', '_')}.md"
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(rec.to_markdown() + "\n")
            return file_path
        except OSError:
            return None

    # -- Querying --------------------------------------------------------

    def query(
        self,
        task_type: str,
        domain: str | None = None,
        k: int = 10,
    ) -> list[dict[str, Any]]:
        """Retrieve historical performance for *task_type*.

        Returns a list of parsed records, sorted by pass_rate desc.
        """
        if self.retriever is None:
            return []

        try:
            query_str = f"historical performance for {task_type}"
            context = self.retriever.get_context_string(query=query_str, k=k)
            # Parse the context back into structured records
            return self._parse_context(context)
        except Exception as exc:
            logger.warning("Truth query failed: %s", exc)
            return []

    def recommend(
        self,
        task_type: str,
        budget: float | None = None,
        k: int = 10,
    ) -> list[tuple[str, float]]:
        """Return ranked list of (agent, expected_pass_rate).

        If *budget* is given, filters to records whose average cost ≤ budget.
        """
        records = self.query(task_type, k=k)

        from collections import defaultdict

        by_agent: defaultdict[str, list[dict]] = defaultdict(list)
        for rec in records:
            by_agent[rec["agent"]].append(rec)

        scored: list[tuple[str, float]] = []
        for agent, recs in by_agent.items():
            if budget is not None:
                avg_cost = sum(r.get("cost_usd", 0) for r in recs) / len(recs)
                if avg_cost > budget:
                    continue
            avg_pass = sum(r.get("pass_rate", 0) for r in recs) / len(recs)
            scored.append((agent, avg_pass))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    # -- Helpers ---------------------------------------------------------

    def _parse_context(self, context: str) -> list[dict[str, Any]]:
        """Naive parser for markdown truth records from KB context."""
        records: list[dict[str, Any]] = []
        current: dict[str, Any] = {}
        for line in context.splitlines():
            line = line.strip()
            if line.startswith("- **Task**:"):
                current = {"task_type": line.split(":", 1)[1].strip()}
            elif line.startswith("- **Agent**:"):
                current["agent"] = line.split(":", 1)[1].strip()
            elif line.startswith("- **Model**:"):
                current["model"] = line.split(":", 1)[1].strip()
            elif line.startswith("- **Pass Rate**:"):
                try:
                    current["pass_rate"] = float(line.split(":", 1)[1].strip().rstrip("%").strip()) / 100.0
                except ValueError:
                    current["pass_rate"] = 0.0
            elif line.startswith("- **Cost**:"):
                try:
                    current["cost_usd"] = float(line.split(":", 1)[1].strip().lstrip("$").strip())
                except ValueError:
                    current["cost_usd"] = 0.0
            elif line.startswith("- **Duration**:"):
                try:
                    current["duration"] = float(line.split(":", 1)[1].strip().rstrip("s").strip())
                except ValueError:
                    current["duration"] = 0.0
            elif line.startswith("- **Domain**:"):
                current["domain"] = line.split(":", 1)[1].strip()
            elif line.startswith("- **Plan**:"):
                current["plan_name"] = line.split(":", 1)[1].strip()
            elif line.startswith("- **Timestamp**:"):
                current["timestamp"] = line.split(":", 1)[1].strip()
                records.append(current)
                current = {}
        if current:
            records.append(current)
        return records
