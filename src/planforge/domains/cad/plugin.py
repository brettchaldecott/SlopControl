"""CAD domain plugin for PlanForge.

Wraps all existing CAD tooling — shape creation, booleans, export,
visualisation, git, file ops — into the :class:`~DomainPlugin` contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from planforge.core.domain_base import DomainPlugin


class CADPlugin(DomainPlugin):
    """PlanForge plugin for 3D CAD design."""

    name = "cad"
    display_name = "CAD Design"

    # -- Tools ---------------------------------------------------------

    def get_tools(self) -> list[Any]:
        from .tools.cad import CAD_TOOLS
        from .tools.visualization import VISUALIZATION_TOOLS
        from .tools.git_ops import GIT_TOOLS
        from .tools.file_ops import FILE_OPS_TOOLS
        return CAD_TOOLS + VISUALIZATION_TOOLS + GIT_TOOLS + FILE_OPS_TOOLS

    # -- Verification -------------------------------------------------

    def get_verifiers(self) -> list[Any]:
        from .verify.geometry import GeometryVerifier
        from .verify.mechanical import MechanicalVerifier
        from .verify.assembly import AssemblyVerifier
        from .verify.printability import PrintabilityVerifier
        return [
            GeometryVerifier(),
            MechanicalVerifier(),
            AssemblyVerifier(),
            PrintabilityVerifier(),
        ]

    # -- Project scaffolding -------------------------------------------

    def scaffold_project(self, project_path: Path) -> None:
        (project_path / "designs").mkdir(parents=True, exist_ok=True)
        (project_path / "exports").mkdir(parents=True, exist_ok=True)
        (project_path / "previews").mkdir(parents=True, exist_ok=True)

    # -- Capabilities ---------------------------------------------------

    def get_capabilities(self) -> list[str]:
        return [
            "3d-modeling",
            "parametric-design",
            "sketch-extrude",
            "boolean-ops",
            "mesh-export",
            "step-export",
            "stl-export",
            "printability-check",
            "assembly-check",
        ]
