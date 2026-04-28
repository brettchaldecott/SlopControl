"""Tests for file operations tools."""

import pytest
from pathlib import Path


class TestFileOpsTools:
    """Test suite for file operations tools."""

    def test_save_design_exists(self):
        """Test save_design_state tool exists."""
        from slopcontrol.tools.file_ops import save_design_state

        assert save_design_state is not None

    def test_load_design_exists(self):
        """Test load_design_state tool exists."""
        from slopcontrol.tools.file_ops import load_design_state

        assert load_design_state is not None

    def test_list_designs_exists(self):
        """Test list_designs tool exists."""
        from slopcontrol.tools.file_ops import list_designs

        assert list_designs is not None

    def test_create_project_exists(self):
        """Test create_project tool exists."""
        from slopcontrol.tools.file_ops import create_project

        assert create_project is not None

    def test_file_ops_tools_list(self):
        """Test that FILE_OPS_TOOLS list contains expected tools."""
        from slopcontrol.tools.file_ops import FILE_OPS_TOOLS

        expected_tools = [
            "save_design_state",
            "load_design_state",
            "list_designs",
            "create_project",
            "delete_design",
        ]

        tool_names = [t.name for t in FILE_OPS_TOOLS]

        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"
