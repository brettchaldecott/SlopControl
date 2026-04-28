"""Competition judgement — purely empirical, no LLM bias.

The judge selects winners based on verifier pass-rate, cost, and
duration.  Optionally consults the historical truth DB to break ties.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .competition import CandidateResult, CompetitionOutcome

logger = logging.getLogger(__name__)


class CompetitionJudge:
    """Select the best candidate from a competition round.

    Strategies:
    - **pass_rate** (default): highest fraction of verifier checks passed
    - **cost**: cheapest candidate
    - **speed**: fastest candidate
    - **hybrid**: pass_rate first, then cost tie-breaker, then speed
    """

    def __init__(self, strategy: str = "hybrid") -> None:
        self.strategy = strategy

    # -- Public API -----------------------------------------------------

    def judge(self, outcome: CompetitionOutcome) -> CandidateResult | None:
        """Evaluate all candidates and return the winner (or None if all failed)."""
        candidates = outcome.candidates
        if not candidates:
            logger.warning("No candidates to judge")
            return None

        # If only one candidate and it passed, it's the winner
        if len(candidates) == 1 and candidates[0].pass_rate >= 1.0:
            return candidates[0]

        if self.strategy == "pass_rate":
            winner = self._by_pass_rate(candidates)
        elif self.strategy == "cost":
            winner = self._by_cost(candidates)
        elif self.strategy == "speed":
            winner = self._by_speed(candidates)
        elif self.strategy == "hybrid":
            winner = self._by_hybrid(candidates)
        else:
            raise ValueError(f"Unknown judge strategy: {self.strategy}")

        if winner is None:
            logger.warning("All candidates failed — no winner selected")
        else:
            logger.info(
                "Winner: %s (pass_rate=%.2f, cost=$%.4f, time=%.1fs)",
                winner.agent_name,
                winner.pass_rate,
                winner.cost_usd,
                winner.duration,
            )

        outcome.winner = winner
        return winner

    # -- Scoring strategies ---------------------------------------------

    def _by_pass_rate(self, candidates: list[CandidateResult]) -> CandidateResult | None:
        best = max(candidates, key=lambda c: c.pass_rate)
        return best if best.pass_rate > 0 else None

    def _by_cost(self, candidates: list[CandidateResult]) -> CandidateResult | None:
        best = min(candidates, key=lambda c: c.cost_usd)
        return best if best.pass_rate > 0 else None

    def _by_speed(self, candidates: list[CandidateResult]) -> CandidateResult | None:
        best = min(candidates, key=lambda c: c.duration)
        return best if best.pass_rate > 0 else None

    def _by_hybrid(self, candidates: list[CandidateResult]) -> CandidateResult | None:
        """Primary: pass_rate.  Tie-breaker 1: lower cost.  Tie-breaker 2: lower duration."""
        scored = [
            (c.pass_rate, -c.cost_usd, -c.duration, c)
            for c in candidates
            if c.pass_rate > 0
        ]
        if not scored:
            return None
        scored.sort(reverse=True)
        return scored[0][3]
