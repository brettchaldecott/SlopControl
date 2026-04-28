"""Cost tracking for every LLM call in SlopControl.

Keeps a running ledger of estimated spend.  Alerts the Conductor
when the budget is exhausted.  Persists to disk so the system can
learn from historical cost data.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_LEDGER_FILE = Path.home() / ".slopcontrol" / "cost_ledger.jsonl"


@dataclass
class CostEntry:
    """A single row in the cost ledger."""

    timestamp: str
    provider: str
    model: str
    task_type: str
    step_index: int
    plan_name: str
    cost_usd: float
    tokens_prompt: int = 0
    tokens_completion: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "provider": self.provider,
            "model": self.model,
            "task_type": self.task_type,
            "step_index": self.step_index,
            "plan_name": self.plan_name,
            "cost_usd": self.cost_usd,
            "tokens_prompt": self.tokens_prompt,
            "tokens_completion": self.tokens_completion,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CostEntry":
        return cls(
            timestamp=data["timestamp"],
            provider=data["provider"],
            model=data["model"],
            task_type=data["task_type"],
            step_index=data["step_index"],
            plan_name=data["plan_name"],
            cost_usd=data["cost_usd"],
            tokens_prompt=data.get("tokens_prompt", 0),
            tokens_completion=data.get("tokens_completion", 0),
        )


class CostTracker:
    """Track estimated LLM spend and enforce budget caps."""

    def __init__(self, daily_budget: float = 5.0) -> None:
        self.daily_budget = daily_budget
        self.entries: list[CostEntry] = []
        self._today: str = datetime.now().strftime("%Y-%m-%d")
        self._budget_exhausted: bool = False

    # -- Recording -------------------------------------------------------

    def record(
        self,
        task_type: str,
        provider: str,
        model: str,
        cost_usd: float,
        step_index: int,
        plan_name: str,
        tokens_prompt: int = 0,
        tokens_completion: int = 0,
    ) -> None:
        """Log a new cost entry and persist to disk."""
        entry = CostEntry(
            timestamp=datetime.now().isoformat(),
            provider=provider,
            model=model,
            task_type=task_type,
            step_index=step_index,
            plan_name=plan_name,
            cost_usd=cost_usd,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
        )
        self.entries.append(entry)
        self._persist(entry)
        logger.info(
            "Cost recorded: $%.4f for %s/%s step %d — budget $%.2f / $%.2f",
            cost_usd, provider, model, step_index,
            self.today_total, self.daily_budget,
        )

    # -- Budget queries --------------------------------------------------

    @property
    def today_total(self) -> float:
        """Sum of all costs from today."""
        today = datetime.now().strftime("%Y-%m-%d")
        return sum(
            e.cost_usd
            for e in self.entries
            if e.timestamp.startswith(today)
        )

    @property
    def remaining_budget(self) -> float:
        return max(0.0, self.daily_budget - self.today_total)

    def can_afford(self, estimated_cost: float) -> bool:
        """Check whether the estimated cost fits in today's budget."""
        if self.remaining_budget < estimated_cost:
            logger.warning(
                "Budget check failed: estimated $%.4f > remaining $%.4f",
                estimated_cost, self.remaining_budget,
            )
            return False
        return True

    # -- Historical queries ----------------------------------------------

    def avg_cost(self, task_type: str, provider: str, model: str) -> float | None:
        """Return average historical cost for a (task, provider, model) combo."""
        matching = [
            e.cost_usd for e in self.entries
            if e.task_type == task_type and e.provider == provider and e.model == model
        ]
        if not matching:
            return None
        return sum(matching) / len(matching)

    # -- Persistence -----------------------------------------------------

    def _persist(self, entry: CostEntry) -> None:
        try:
            _LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
            with _LEDGER_FILE.open("a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as exc:
            logger.warning("Failed to persist cost ledger: %s", exc)

    def load_history(self) -> None:
        """Load all historical entries from the ledger file."""
        if not _LEDGER_FILE.exists():
            return
        try:
            entries: list[CostEntry] = []
            with _LEDGER_FILE.open("r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(CostEntry.from_dict(json.loads(line)))
                    except Exception:
                        continue
            self.entries = entries
            logger.info("Loaded %d historical cost entries", len(entries))
        except Exception as exc:
            logger.warning("Failed to load cost ledger: %s", exc)
