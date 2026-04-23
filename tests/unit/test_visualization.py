"""Tests for visualization tools."""

import pytest


class TestVisualizationTools:
    """Test suite for visualization tools."""

    def test_render_preview_exists(self):
        """Test render_preview tool exists."""
        from planforge.tools.visualization import render_preview

        assert render_preview is not None

    def test_display_preview_exists(self):
        """Test display_preview tool exists."""
        from planforge.tools.visualization import display_preview

        assert display_preview is not None

    def test_display_multiview_exists(self):
        """Test display_multiview tool exists."""
        from planforge.tools.visualization import display_multiview

        assert display_multiview is not None

    def test_compare_designs_exists(self):
        """Test compare_designs tool exists."""
        from planforge.tools.visualization import compare_designs

        assert compare_designs is not None

    def test_get_info_exists(self):
        """Test get_model_info_detailed tool exists."""
        from planforge.tools.visualization import get_model_info_detailed

        assert get_model_info_detailed is not None

    def test_visualization_tools_list(self):
        """Test that VISUALIZATION_TOOLS list contains expected tools."""
        from planforge.tools.visualization import VISUALIZATION_TOOLS

        expected_tools = [
            "render_preview",
            "display_preview",
            "display_multiview",
            "get_model_info_detailed",
            "compare_designs",
        ]

        tool_names = [t.name for t in VISUALIZATION_TOOLS]

        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"
