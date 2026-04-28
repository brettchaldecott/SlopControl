"""Tests for the competition manager and cost tracker."""

import pytest
from pathlib import Path

from slopcontrol.core.orchestrator.competition import CandidateConfig, CandidateResult, CompetitionManager
from slopcontrol.core.orchestrator.judge import CompetitionJudge
from slopcontrol.core.orchestrator.cost_tracker import CostTracker, CostEntry
from slopcontrol.core.orchestrator.registry import PluginRegistry
from slopcontrol.core.verify.base import VerificationResult


class TestCompetitionJudge:
    def test_pass_rate_strategy(self):
        j = CompetitionJudge(strategy="pass_rate")
        candidates = [
            CandidateResult(agent_name="a", model_spec=None, verifier_results=[], pass_rate=0.5),
            CandidateResult(agent_name="b", model_spec=None, verifier_results=[], pass_rate=0.9),
        ]
        outcome = type("O", (), {"candidates": candidates, "winner": None})()
        winner = j.judge(outcome)
        assert winner is not None
        assert winner.agent_name == "b"

    def test_hybrid_tie_breaker_cost(self):
        j = CompetitionJudge(strategy="hybrid")
        candidates = [
            CandidateResult(agent_name="a", model_spec=None, verifier_results=[], pass_rate=1.0, cost_usd=0.10),
            CandidateResult(agent_name="b", model_spec=None, verifier_results=[], pass_rate=1.0, cost_usd=0.05),
        ]
        outcome = type("O", (), {"candidates": candidates, "winner": None})()
        winner = j.judge(outcome)
        assert winner is not None
        assert winner.agent_name == "b"

    def test_all_fails_returns_none(self):
        j = CompetitionJudge(strategy="pass_rate")
        candidates = [
            CandidateResult(agent_name="a", model_spec=None, verifier_results=[], pass_rate=0.0),
        ]
        outcome = type("O", (), {"candidates": candidates, "winner": None})()
        winner = j.judge(outcome)
        assert winner is None


class TestCostTracker:
    def test_record_and_sum(self, tmp_path, monkeypatch):
        # Isolate ledger to temp dir
        monkeypatch.setattr(
            "slopcontrol.core.orchestrator.cost_tracker._LEDGER_FILE",
            tmp_path / "cost.jsonl",
        )
        ct = CostTracker(daily_budget=1.0)
        ct.record(task_type="code", provider="openai", model="gpt-4o-mini", cost_usd=0.10, step_index=0, plan_name="test")
        ct.record(task_type="code", provider="openai", model="gpt-4o-mini", cost_usd=0.15, step_index=1, plan_name="test")
        assert ct.today_total == pytest.approx(0.25)
        assert ct.remaining_budget == pytest.approx(0.75)
        assert ct.can_afford(0.5) is True
        assert ct.can_afford(0.8) is False
        assert ct.can_afford(0.2) is True

    def test_avg_cost(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "slopcontrol.core.orchestrator.cost_tracker._LEDGER_FILE",
            tmp_path / "cost.jsonl",
        )
        ct = CostTracker(daily_budget=10.0)
        ct.record(task_type="api", provider="grok", model="grok-3-beta", cost_usd=0.05, step_index=0, plan_name="p1")
        ct.record(task_type="api", provider="grok", model="grok-3-beta", cost_usd=0.07, step_index=1, plan_name="p1")
        avg = ct.avg_cost("api", "grok", "grok-3-beta")
        assert avg == pytest.approx(0.06)

    def test_load_history(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "slopcontrol.core.orchestrator.cost_tracker._LEDGER_FILE",
            tmp_path / "cost.jsonl",
        )
        ct1 = CostTracker()
        ct1.record(task_type="t", provider="p", model="m", cost_usd=0.1, step_index=0, plan_name="p")
        ct2 = CostTracker()
        ct2.load_history()
        assert ct2.today_total == pytest.approx(0.1)


class TestCompetitionManager:
    def test_init(self):
        reg = PluginRegistry()
        reg.auto_discover()
        cm = CompetitionManager(reg)
        assert cm.max_workers == 3

    def test_estimate_cost(self):
        reg = PluginRegistry()
        cm = CompetitionManager(reg)
        cfg = CandidateConfig(agent_name="grok", model_spec="grok:grok-3-beta")
        cost = cm._estimate_cost(cfg, {}, 120)
        assert cost > 0
