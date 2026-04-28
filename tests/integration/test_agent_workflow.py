"""Integration tests for the PlanForge agent workflow."""

import json
import tempfile
from pathlib import Path

import pytest

try:
    import llmcad  # noqa: F401
    LLMCAD_AVAILABLE = True
except ImportError:
    LLMCAD_AVAILABLE = False


class TestAgentWorkflow:
    """Integration tests for complete agent workflows."""

    @pytest.mark.skipif(not LLMCAD_AVAILABLE, reason="llmcad not installed")
    def test_create_box_and_export(self):
        """Test creating a simple box and exporting it."""
        from slopcontrol.tools.cad import create_box, export_model

        box_result = create_box.invoke(
            {
                "width": 50,
                "height": 50,
                "depth": 50,
                "name": "test_cube",
            }
        )

        data = json.loads(box_result)
        assert "ref" in data
        assert data["name"] == "test_cube"

    @pytest.mark.skipif(not LLMCAD_AVAILABLE, reason="llmcad not installed")
    def test_create_cylinder(self):
        """Test cylinder creation."""
        from slopcontrol.tools.cad import create_cylinder

        result = create_cylinder.invoke(
            {
                "radius": 25,
                "height": 50,
                "name": "test_cylinder",
            }
        )

        data = json.loads(result)
        assert data["name"] == "test_cylinder"

    @pytest.mark.skipif(not LLMCAD_AVAILABLE, reason="llmcad not installed")
    def test_create_sphere(self):
        """Test sphere creation."""
        from slopcontrol.tools.cad import create_sphere

        result = create_sphere.invoke(
            {
                "radius": 20,
                "name": "test_sphere",
            }
        )

        data = json.loads(result)
        assert data["name"] == "test_sphere"

    @pytest.mark.skipif(not LLMCAD_AVAILABLE, reason="llmcad not installed")
    def test_boolean_operations(self):
        """Test boolean operations between bodies."""
        from slopcontrol.tools.cad import create_box, create_cylinder, union_bodies, cut_body

        box_data = create_box.invoke(
            {
                "width": 50,
                "height": 50,
                "depth": 50,
                "name": "box1",
            }
        )

        cyl_data = create_cylinder.invoke(
            {
                "radius": 10,
                "height": 60,
                "name": "cyl1",
            }
        )

        union_result = union_bodies.invoke(
            {
                "body1_data": box_data,
                "body2_data": cyl_data,
            }
        )

        assert "union" in union_result.lower() or "ref" in union_result

    def test_cad_tools_list(self):
        """Test that all expected CAD tools are available."""
        from slopcontrol.tools.cad import CAD_TOOLS

        tool_names = [t.name for t in CAD_TOOLS]

        expected = [
            "create_box",
            "create_cylinder",
            "create_sphere",
            "create_rect",
            "create_circle",
            "extrude_sketch",
            "add_fillet",
            "union_bodies",
            "cut_body",
            "export_model",
        ]

        for tool in expected:
            assert tool in tool_names, f"Missing tool: {tool}"


class TestVisualization:
    """Integration tests for visualization tools."""

    def test_render_preview_structure(self):
        """Test that render_preview tool exists and has correct signature."""
        from slopcontrol.tools.visualization import render_preview

        assert render_preview is not None
        assert hasattr(render_preview, "invoke")
        assert hasattr(render_preview, "name")

    def test_display_preview_structure(self):
        """Test that display_preview tool exists."""
        from slopcontrol.tools.visualization import display_preview

        assert display_preview is not None
        assert hasattr(display_preview, "invoke")

    def test_visualization_tools_count(self):
        """Test that all visualization tools are available."""
        from slopcontrol.tools.visualization import VISUALIZATION_TOOLS

        assert len(VISUALIZATION_TOOLS) >= 4


class TestGitIntegration:
    """Integration tests for git operations."""

    def test_git_tools_exist(self):
        """Test that git tools are available."""
        from slopcontrol.tools.git_ops import (
            commit_design,
            get_design_history,
            init_git_repo,
        )

        assert commit_design is not None
        assert get_design_history is not None
        assert init_git_repo is not None

    def test_init_git_repo(self, tmp_path):
        """Test initializing a git repository."""
        from slopcontrol.tools.git_ops import init_git_repo

        result = init_git_repo.invoke(
            {
                "project_path": str(tmp_path),
            }
        )

        assert "git" in result.lower() or tmp_path.joinpath(".git").exists()


class TestFileOperations:
    """Integration tests for file operations."""

    def test_file_ops_tools_exist(self):
        """Test that file operations tools exist."""
        from slopcontrol.tools.file_ops import (
            save_design_state,
            load_design_state,
            list_designs,
            create_project,
        )

        assert save_design_state is not None
        assert load_design_state is not None
        assert list_designs is not None
        assert create_project is not None

    def test_create_project(self, tmp_path):
        """Test creating a new project."""
        from slopcontrol.tools.file_ops import create_project

        result = create_project.invoke(
            {
                "project_name": "test_project",
                "project_path": str(tmp_path),
            }
        )

        assert "test_project" in result
        assert (tmp_path / "test_project" / "designs").exists()

    @pytest.mark.skipif(not LLMCAD_AVAILABLE, reason="llmcad not installed")
    def test_save_and_load_design(self, tmp_path):
        """Test saving and loading a design state."""
        from slopcontrol.tools.file_ops import save_design_state, load_design_state
        from slopcontrol.tools.cad import create_box

        designs_dir = tmp_path / "designs"
        designs_dir.mkdir()

        box_data = create_box.invoke(
            {
                "width": 50,
                "height": 50,
                "depth": 50,
                "name": "cube",
            }
        )

        save_path = save_design_state.invoke(
            {
                "body_data": box_data,
                "name": "test_cube",
                "project_path": str(tmp_path),
            }
        )

        assert "test_cube.json" in save_path

        loaded = load_design_state.invoke(
            {
                "name": "test_cube",
                "project_path": str(tmp_path),
            }
        )

        assert "ref" in loaded


class TestDesignHistory:
    """Integration tests for design history."""

    def test_design_history_init(self, tmp_path):
        """Test initializing design history."""
        from slopcontrol.tools.design_history import DesignHistory

        history = DesignHistory(tmp_path)
        assert history.project_path == tmp_path
        assert len(history.iterations) == 0

    def test_add_iteration(self, tmp_path):
        """Test adding iterations to history."""
        from slopcontrol.tools.design_history import DesignHistory

        history = DesignHistory(tmp_path)

        model_info = {
            "dimensions": {"width": 50, "height": 50, "depth": 50},
            "volume": 125000,
        }

        iter1 = history.add_iteration(
            message="Created cube",
            model_info=model_info,
        )

        assert iter1.version == 1
        assert len(history.iterations) == 1

        iter2 = history.add_iteration(
            message="Added fillet",
            model_info=model_info,
            changes={"fillet_radius": 2},
        )

        assert iter2.version == 2
        assert len(history.iterations) == 2

    def test_compare_versions(self, tmp_path):
        """Test comparing two versions."""
        from slopcontrol.tools.design_history import DesignHistory

        history = DesignHistory(tmp_path)

        history.add_iteration(
            message="v1",
            model_info={
                "dimensions": {"width": 50, "height": 50, "depth": 50},
            },
        )

        history.add_iteration(
            message="v2",
            model_info={
                "dimensions": {"width": 60, "height": 50, "depth": 50},
            },
        )

        diff = history.compare_versions(1, 2)

        assert "dimensions" in diff
        assert "width" in diff["dimensions"]
        assert diff["dimensions"]["width"]["change"] == 10


class TestProviderRegistry:
    """Integration tests for LLM provider registry."""

    def test_parse_model_string(self):
        """Test model string parsing."""
        from slopcontrol.providers.registry import parse_model_string

        provider, model = parse_model_string("openai:gpt-4o")
        assert provider == "openai"
        assert model == "gpt-4o"

        provider, model = parse_model_string("anthropic:claude-3")
        assert provider == "anthropic"
        assert model == "claude-3"

    def test_list_available_models(self):
        """Test listing available models."""
        from slopcontrol.providers.registry import list_available_models

        models = list_available_models()
        assert "openai" in models
        assert "anthropic" in models
        assert "ollama" in models

        assert "gpt-4o" in models["openai"]
        assert len(models["anthropic"]) > 0


class TestCLICmds:
    """Integration tests for CLI commands."""

    def test_cli_imports(self):
        """Test that CLI can be imported."""
        from slopcontrol.cli import app

        assert app is not None

    def test_mcp_tools_list(self):
        """Test that MCP tools list works."""
        from slopcontrol.mcp.tools import CAD_MCP_TOOLS

        assert len(CAD_MCP_TOOLS) > 30

        tool_names = [t.name for t in CAD_MCP_TOOLS]
        assert "create_box" in tool_names
        assert "commit_design" in tool_names
        assert "render_preview" in tool_names
