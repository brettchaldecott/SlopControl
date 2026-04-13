"""Tests for git operations tools."""

import pytest
from pathlib import Path


class TestGitTools:
    """Test suite for git operation tools."""

    def test_commit_tool_exists(self):
        """Test commit_design tool exists."""
        from cadai.tools.git_ops import commit_design

        assert commit_design is not None

    def test_history_tool_exists(self):
        """Test get_design_history tool exists."""
        from cadai.tools.git_ops import get_design_history

        assert get_design_history is not None

    def test_restore_tool_exists(self):
        """Test restore_version tool exists."""
        from cadai.tools.git_ops import restore_version

        assert restore_version is not None

    def test_branch_tool_exists(self):
        """Test create_experiment_branch tool exists."""
        from cadai.tools.git_ops import create_experiment_branch

        assert create_experiment_branch is not None

    def test_init_tool_exists(self):
        """Test init_git_repo tool exists."""
        from cadai.tools.git_ops import init_git_repo

        assert init_git_repo is not None

    def test_git_tools_list(self):
        """Test that GIT_TOOLS list contains expected tools."""
        from cadai.tools.git_ops import GIT_TOOLS

        expected_tools = [
            "commit_design",
            "get_design_history",
            "restore_version",
            "create_experiment_branch",
            "merge_experiment",
            "init_git_repo",
        ]

        tool_names = [t.name for t in GIT_TOOLS]

        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"
