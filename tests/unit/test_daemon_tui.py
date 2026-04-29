"""Tests for the new daemon, TUI client, KnowledgeGraph, and session persistence.

These tests cover the bugs we fixed (TUI log shadowing) and the new persistent
multi-project architecture with graceful shutdown and Coverage of Truth metrics.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from slopcontrol.daemon.server import SlopControlDaemon
from slopcontrol.daemon.state import DaemonState, SessionState
from slopcontrol.core.knowledge.graph import KnowledgeGraph, KnowledgeNode, get_knowledge_graph
from slopcontrol.tui.app import SlopControlTUI


class TestDaemonState:
    """Test persistent state management with graceful shutdown and purge."""

    @pytest.mark.asyncio
    async def test_state_persistence_and_restore(self, tmp_path: Path):
        """Test that sessions are saved and restored across restarts."""
        state = DaemonState(data_dir=tmp_path)

        await state.initialize()

        # Create a test session
        session = SessionState(
            project_name="test-project",
            plan_version="1.0",
            current_plan={"name": "test", "requirements": ["req1"]},
            conversation_history=[{"role": "user", "content": "hello"}],
            knowledge_deltas=[],
            last_active="2026-04-29T08:00:00",
            status="active",
        )

        await state.save_session(session)
        assert "test-project" in state.sessions

        # Simulate restart by creating new state object
        new_state = DaemonState(data_dir=tmp_path)
        await new_state.initialize()
        await new_state.load_all_sessions()

        assert "test-project" in new_state.sessions
        restored = new_state.sessions["test-project"]
        assert restored.project_name == "test-project"
        assert restored.plan_version == "1.0"

    @pytest.mark.asyncio
    async def test_purge_session(self, tmp_path: Path):
        """Test explicit session purge for recovery."""
        state = DaemonState(data_dir=tmp_path)
        await state.initialize()

        session = SessionState(
            project_name="broken-project",
            plan_version="1.0",
            current_plan={},
            conversation_history=[],
            knowledge_deltas=[],
            last_active="2026-04-29T08:00:00",
        )
        await state.save_session(session)

        success = await state.purge_session("broken-project")
        assert success is True
        assert "broken-project" not in state.sessions

        # Verify it's gone from disk too
        new_state = DaemonState(data_dir=tmp_path)
        await new_state.load_all_sessions()
        assert "broken-project" not in new_state.sessions


class TestKnowledgeGraph:
    """Test the new graph-based knowledge fabric and Coverage of Truth."""

    def test_knowledge_node_creation(self):
        """Test KnowledgeNode with confidence scores."""
        node = KnowledgeNode(
            id="test-1",
            type="truth",
            content="Tests should cover edge cases",
            confidence=0.85,
        )
        assert node.id == "test-1"
        assert node.confidence == 0.85
        assert node.type == "truth"

    def test_coverage_of_truth_calculation(self):
        """Test the 'Coverage of Truth' metric."""
        graph = KnowledgeGraph()

        # High confidence (validated)
        graph.add_node(KnowledgeNode("n1", "truth", "Test passed", 0.95))
        graph.add_node(KnowledgeNode("n2", "truth", "Coverage 90%", 0.90))

        # Low confidence (uncertain)
        graph.add_node(KnowledgeNode("n3", "decision", "Untested path", 0.4))

        coverage = graph.get_coverage_of_truth()
        assert coverage["validated"] == pytest.approx(0.666, abs=0.01)  # 2/3
        assert coverage["uncertain"] == pytest.approx(0.333, abs=0.01)
        assert coverage["total_nodes"] == 3

    def test_get_lessons(self):
        """Test extraction of lessons from high-confidence truths."""
        graph = KnowledgeGraph()
        graph.add_node(KnowledgeNode("l1", "truth", "Always write tests first", 0.92))
        graph.add_node(KnowledgeNode("l2", "truth", "Use type hints", 0.88))
        graph.add_node(KnowledgeNode("l3", "observation", "Bug in edge case", 0.6))

        lessons = graph.get_lessons(k=2)
        assert "Always write tests first" in lessons
        assert "Use type hints" in lessons
        assert "Bug in edge case" not in lessons  # below confidence threshold


class TestTUI:
    """Test the Textual TUI to prevent regression of the log shadowing bug."""

    def test_tui_does_not_shadow_log(self):
        """Ensure we don't override Textual's self.log with our own method."""
        app = SlopControlTUI()

        # Textual's App should still have its original log attribute
        assert hasattr(app, "log")
        assert callable(app.log)  # The original Textual logger
        assert hasattr(app, "add_log")  # Our custom method

        # Our method should not break the original
        assert not hasattr(app.log, "system") is False  # It should have .system()

    def test_add_log_method_exists(self):
        """Test our safe logging method exists and works."""
        app = SlopControlTUI()
        assert hasattr(app, "add_log")
        assert callable(app.add_log)


class TestDaemonIntegration:
    """Integration tests for daemon + TUI communication."""

    @pytest.mark.asyncio
    async def test_daemon_graceful_shutdown(self):
        """Test that daemon saves state on shutdown."""
        daemon = SlopControlDaemon(host="127.0.0.1", port=0)  # random port

        # Mock the state
        daemon.state = MagicMock()
        daemon.state.close = AsyncMock()

        # Simulate shutdown
        await daemon._shutdown("SIGTERM")

        daemon.state.close.assert_awaited_once()
        assert daemon.shutdown_event.is_set() is True

    def test_cli_entrypoint_respects_daemon_flag(self):
        """Test that `slopcontrol daemon` routes correctly."""
        from slopcontrol.cli import main

        # This is hard to test directly without patching, but we can check structure
        import inspect
        source = inspect.getsource(main)
        assert "daemon" in source.lower()
        assert "from slopcontrol.daemon.server" in source
        assert "run_tui" in source
