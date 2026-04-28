"""Tests for the plugin registry."""

import pytest

from planforge.core.orchestrator.registry import PluginRegistry
from planforge.domains.cad import CADPlugin
from planforge.domains.code import CodePlugin


class TestPluginRegistry:
    def test_register_cad_plugin(self):
        reg = PluginRegistry()
        reg.register(CADPlugin())
        assert reg.has("cad")
        assert reg.get("cad").name == "cad"

    def test_register_code_plugin(self):
        reg = PluginRegistry()
        reg.register(CodePlugin())
        assert reg.has("code")

    def test_list_domains(self):
        reg = PluginRegistry()
        reg.register(CADPlugin())
        reg.register(CodePlugin())
        assert sorted(reg.list_domains()) == ["cad", "code"]

    def test_get_unknown_domain(self):
        reg = PluginRegistry()
        with pytest.raises(KeyError):
            reg.get("unknown")

    def test_auto_discover(self):
        reg = PluginRegistry()
        count = reg.auto_discover()
        assert count >= 2
        assert reg.has("cad")
        assert reg.has("code")

    def test_external_adapters(self):
        reg = PluginRegistry()
        assert reg.get_external_adapter("opencode") is not None
        assert reg.get_external_adapter("cursor") is not None
        assert reg.get_external_adapter("cursor") is not None


class TestCADPlugin:
    def test_tools(self):
        p = CADPlugin()
        tools = p.get_tools()
        assert len(tools) > 30
        names = [t.name for t in tools]
        assert "create_box" in names
        assert "render_preview" in names

    def test_verifiers(self):
        p = CADPlugin()
        verifiers = p.get_verifiers()
        assert len(verifiers) == 4

    def test_scaffold(self, tmp_path):
        p = CADPlugin()
        p.scaffold_project(tmp_path)
        assert (tmp_path / "designs").exists()
        assert (tmp_path / "exports").exists()
        assert (tmp_path / "previews").exists()

    def test_capabilities(self):
        p = CADPlugin()
        caps = p.get_capabilities()
        assert "3d-modeling" in caps

    def test_prompt(self):
        p = CADPlugin()
        prompt = p.get_agent_prompt()
        assert "CAD" in prompt or "cad" in prompt


class TestCodePlugin:
    def test_tools(self):
        p = CodePlugin()
        tools = p.get_tools()
        assert len(tools) > 10
        names = [t.name for t in tools]
        assert "write_code" in names
        assert "run_tests" in names

    def test_verifiers(self):
        p = CodePlugin()
        verifiers = p.get_verifiers()
        assert len(verifiers) == 3

    def test_scaffold(self, tmp_path):
        p = CodePlugin()
        p.scaffold_project(tmp_path)
        assert (tmp_path / "src").exists()
        assert (tmp_path / "tests").exists()
        assert (tmp_path / "docs").exists()

    def test_capabilities(self):
        p = CodePlugin()
        caps = p.get_capabilities()
        assert "code-gen" in caps

    def test_prompt(self):
        p = CodePlugin()
        prompt = p.get_agent_prompt()
        assert "software" in prompt or "code" in prompt
