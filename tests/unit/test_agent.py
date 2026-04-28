"""Tests for the SlopControl agent factory."""

import pytest


class TestAgentFactory:
    """Test suite for agent creation."""

    def test_create_cad_agent_import(self):
        """Test that create_cad_agent can be imported."""
        from slopcontrol import create_cad_agent

        assert create_cad_agent is not None

    def test_run_design_session_import(self):
        """Test that run_design_session can be imported."""
        from slopcontrol.agent import run_design_session

        assert run_design_session is not None

    def test_cad_tools_import(self):
        """Test that CAD_TOOLS can be imported."""
        from slopcontrol import CAD_TOOLS

        assert CAD_TOOLS is not None
        assert isinstance(CAD_TOOLS, list)
        assert len(CAD_TOOLS) > 0
