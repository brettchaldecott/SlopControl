"""Tests for the orchestrator Conductor and DispatchEngine."""

import pytest

from slopcontrol.core.orchestrator import Conductor, PluginRegistry
from slopcontrol.core.orchestrator.dispatch import DispatchEngine, OrchestrationError
from slopcontrol.core.orchestrator.protocol import StepStatus
from slopcontrol.core.plan.schema import DesignPlan


class TestDispatchEngine:
    def test_cad_explicit_domain(self):
        reg = PluginRegistry()
        reg.auto_discover()
        engine = DispatchEngine(reg)

        step = {"domain": "cad", "description": "Create a mounting plate"}
        name, typ = engine.select_agent(step, DesignPlan(name="test", domain="code"))
        assert name == "cad"

    def test_fallback_to_plan_domain(self):
        reg = PluginRegistry()
        reg.auto_discover()
        engine = DispatchEngine(reg)

        step = {"description": "Create a mounting plate"}
        name, typ = engine.select_agent(step, DesignPlan(name="test", domain="cad"))
        assert name == "cad"

    def test_unknown_domain_raises(self):
        reg = PluginRegistry()
        engine = DispatchEngine(reg)

        step = {"domain": "unknown"}
        with pytest.raises(OrchestrationError):
            engine.select_agent(step, DesignPlan(name="test", domain="unknown"))


class TestConductor:
    def test_init(self):
        reg = PluginRegistry()
        reg.auto_discover()
        c = Conductor(registry=reg)
        assert c.registry.has("cad")
        assert c.registry.has("code")

    def test_run_plan_empty(self, tmp_path):
        reg = PluginRegistry()
        reg.auto_discover()
        c = Conductor(registry=reg)

        plan = DesignPlan(name="empty", domain="code", requirements=["do nothing"])
        result = c.run_plan(plan, tmp_path)

        assert result["success"] is True
        assert result["artifacts"] == []

    def test_run_plan_creates_directories(self, tmp_path):
        reg = PluginRegistry()
        reg.auto_discover()
        c = Conductor(registry=reg)

        plan = DesignPlan(name="test", domain="code", requirements=["create module"])
        c.run_plan(plan, tmp_path)

        assert (tmp_path / "src").exists()
        assert (tmp_path / "tests").exists()

    def test_checkpoint_saves(self, tmp_path):
        reg = PluginRegistry()
        reg.auto_discover()
        c = Conductor(registry=reg)

        plan = DesignPlan(name="checkpoint_test", domain="code")
        c.run_plan(plan, tmp_path)

        from slopcontrol.core.orchestrator.persistence import exists
        assert exists(tmp_path)

    def test_state_roundtrip(self, tmp_path):
        from slopcontrol.core.orchestrator.persistence import save, load
        from slopcontrol.core.orchestrator.state import OrchestrationState
        from slopcontrol.core.plan.renderer import render_plan

        plan = DesignPlan(name="rt", domain="code")
        render_plan(plan, tmp_path / "plan_forge.md")
        state = OrchestrationState(plan=plan, project_dir=tmp_path)
        state.mark_step(0, StepStatus.COMPLETED)
        save(state, tmp_path)
        restored = load(tmp_path)
        assert restored.plan.name == "rt"
        assert restored.step_states[0] == StepStatus.COMPLETED
