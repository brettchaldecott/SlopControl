"""Tests for git operations tools."""

import pytest
from pathlib import Path


class TestGitTools:
    """Test suite for git operation tools."""

    def test_commit_tool_exists(self):
        """Test commit tool exists."""
        from slopcontrol.domains.code.tools.git_ops import commit
        assert commit is not None

    def test_history_tool_exists(self):
        """Test get_history tool exists."""
        from slopcontrol.domains.code.tools.git_ops import get_history
        assert get_history is not None

    def test_init_tool_exists(self):
        """Test init_git_repo tool exists."""
        from slopcontrol.domains.code.tools.git_ops import init_git_repo
        assert init_git_repo is not None

    def test_git_tools_list(self):
        """Test that GIT_TOOLS list contains expected tools."""
        from slopcontrol.domains.code.tools.git_ops import GIT_TOOLS
        assert len(GIT_TOOLS) > 0
        tool_names = [t.name for t in GIT_TOOLS]
        assert "commit" in tool_names
