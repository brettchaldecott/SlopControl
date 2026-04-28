"""Tests for the plugin registry."""

import pytest

from slopcontrol.core.orchestrator.registry import PluginRegistry
from slopcontrol.domains.code import CodePlugin


class TestPluginRegistry:
    def test_register_code_plugin(self):
        reg = PluginRegistry()
        reg.register(CodePlugin())
        assert reg.has("code")
        assert reg.get("code").name == "code"

    def test_list_domains(self):
        reg = PluginRegistry()
        reg.register(CodePlugin())
        assert sorted(reg.list_domains()) == ["code"]

    def test_get_unknown_domain(self):
        reg = PluginRegistry()
        with pytest.raises(KeyError):
            reg.get("unknown")

    def test_auto_discover(self):
        reg = PluginRegistry()
        count = reg.auto_discover()
        assert count >= 1
        assert reg.has("code")

    def test_external_adapters(self):
        reg = PluginRegistry()
        assert reg.get_external_adapter("opencode") is not None
        assert reg.get_external_adapter("cursor") is not None


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
