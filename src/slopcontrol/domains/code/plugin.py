"""Code domain plugin for SlopControl.

Provides tools for software development: file I/O, testing, linting,
dependency management, and version control.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from slopcontrol.core.domain_base import DomainPlugin


class CodePlugin(DomainPlugin):
    """SlopControl plugin for software development."""

    name = "code"
    display_name = "Software Development"

    # -- Tools ---------------------------------------------------------

    def get_tools(self) -> list[Any]:
        from .tools.code import CODE_TOOLS
        from .tools.file_ops import FILE_TOOLS
        from .tools.git_ops import GIT_TOOLS
        from .tools.test_runner import TEST_TOOLS
        from .tools.dependency_manager import DEP_TOOLS
        return CODE_TOOLS + FILE_TOOLS + GIT_TOOLS + TEST_TOOLS + DEP_TOOLS

    # -- Verification -------------------------------------------------

    def get_verifiers(self) -> list[Any]:
        from .verify.pytest import PytestVerifier
        from .verify.mypy import MypyVerifier
        from .verify.coverage import CoverageVerifier
        return [
            PytestVerifier(),
            MypyVerifier(),
            CoverageVerifier(),
        ]

    # -- Project scaffolding -------------------------------------------

    def scaffold_project(self, project_path: Path) -> None:
        (project_path / "src").mkdir(parents=True, exist_ok=True)
        (project_path / "tests").mkdir(parents=True, exist_ok=True)
        (project_path / "docs").mkdir(parents=True, exist_ok=True)
        (project_path / ".slopcontrol" / "vault").mkdir(parents=True, exist_ok=True)

        gitignore = project_path / ".gitignore"
        gitignore_lines = [
            "# SlopControl runtime state\n",
            ".slopcontrol/orchestration_state.json\n",
            ".slopcontrol/checkpoints/\n",
            ".slopcontrol/competition/\n",
            "# Keep vault notes in version control\n",
            "!.slopcontrol/vault/\n",
            "\n",
            "# Python\n",
            "__pycache__/\n",
            "*.py[cod]\n",
            ".venv/\n",
            "venv/\n",
            "\n",
            "# IDE\n",
            ".idea/\n",
            ".vscode/\n",
        ]
        if not gitignore.exists():
            gitignore.write_text("".join(gitignore_lines), encoding="utf-8")

    # -- Capabilities ---------------------------------------------------

    def get_capabilities(self) -> list[str]:
        return [
            "code-gen",
            "refactoring",
            "test-gen",
            "test-run",
            "type-check",
            "lint",
            "dependency-mgmt",
            "doc-gen",
        ]
