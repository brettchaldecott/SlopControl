"""Code domain plugin for PlanForge.

Provides tools for software development: file I/O, testing, linting,
dependency management, and version control.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from planforge.core.domain_base import DomainPlugin


class CodePlugin(DomainPlugin):
    """PlanForge plugin for software development."""

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
