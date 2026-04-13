"""Tests for visualization tools."""

import pytest


class TestVisualizationTools:
    """Test suite for visualization tools."""

    def test_render_preview_exists(self):
        """Test render_preview tool exists."""
        from cadai.tools.visualization import render_preview

        assert render_preview is not None

    def test_display_preview_exists(self):
        """Test display_preview_in_terminal tool exists."""
        from cadai.tools.visualization import display_preview_in_terminal

        assert display_preview_in_terminal is not None

    def test_get_info_exists(self):
        """Test get_model_info_detailed tool exists."""
        from cadai.tools.visualization import get_model_info_detailed

        assert get_model_info_detailed is not None

    def test_visualization_tools_list(self):
        """Test that VISUALIZATION_TOOLS list contains expected tools."""
        from cadai.tools.visualization import VISUALIZATION_TOOLS

        expected_tools = [
            "render_preview",
            "display_preview_in_terminal",
            "get_model_info_detailed",
        ]

        tool_names = [t.name for t in VISUALIZATION_TOOLS]

        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"
