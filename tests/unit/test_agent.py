"""Tests for the SlopControl agent factory."""

import pytest


class TestAgentFactory:
    """Test suite for agent creation."""

    def test_create_agent_import(self):
        """Test that create_agent can be imported."""
        from slopcontrol import create_agent
        assert create_agent is not None

    def test_run_design_session_import(self):
        """Test that run_design_session can be imported."""
        from slopcontrol.agent import run_design_session
        assert run_design_session is not None

    def test_create_agent_function_signature(self):
        """Test that create_agent accepts expected arguments."""
        from slopcontrol.agent import create_agent
        import inspect
        sig = inspect.signature(create_agent)
        params = list(sig.parameters.keys())
        assert "domain" in params
        assert "model" in params
        assert "provider" in params
        assert "project_dir" in params
