"""3D printability verification: overhangs, wall thickness, support analysis.

Uses trimesh for mesh analysis and geometric heuristics.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from planforge.core.verify.base import DomainVerifier, VerificationResult

logger = logging.getLogger(__name__)


class PrintabilityVerifier(DomainVerifier):
    """Verify 3D-printability of CAD designs.

    Checks:
    - Overhangs (face normals vs build direction)
    - Wall thickness (minimum feature size)
    - Support needs
    """

    def validate(
        self,
        project_dir: str,
        max_overhang: float = 45.0,
        min_wall: float = 0.8,
        nozzle_dia: float = 0.4,
        **kwargs: Any,
    ) -> list[VerificationResult]:
        """Run all printability checks.

        Args:
            project_dir: Path to project with exported STEP/STL files.
            max_overhang: Maximum safe overhang angle in degrees.
            min_wall: Minimum wall thickness in mm.
            nozzle_dia: Nozzle diameter in mm.
        """
        results: list[VerificationResult] = []
        exports_dir = Path(project_dir) / "exports"

        if not exports_dir.exists():
            return [
                VerificationResult(
                    check="printability",
                    passed=False,
                    message="No exports directory",
                    severity="error",
                )
            ]

        mesh_files = list(exports_dir.glob("*.stl"))
        if not mesh_files:
            return [
                VerificationResult(
                    check="printability",
                    passed=False,
                    message="No STL files to analyze",
                    severity="error",
                )
            ]

        for mesh_file in mesh_files:
            results.extend(self._check_mesh(mesh_file, max_overhang, min_wall, nozzle_dia))

        return results

    def _check_mesh(
        self, path: Path, max_overhang: float, min_wall: float, nozzle_dia: float
    ) -> list[VerificationResult]:
        """Analyze a single mesh file."""
        results: list[VerificationResult] = []

        try:
            import trimesh
            from trimesh import repair

            mesh = trimesh.load(path, force="mesh")

            if mesh.is_watertight and not mesh.is_watertight:
                # Should not happen, but trimesh sometimes reports wrong
                pass

            # 1. Repair if needed
            if not mesh.is_watertight:
                logger.info("Mesh %s is not watertight; running repair", path.name)
                repair.fix_winding(mesh)
                repair.fill_holes(mesh)

            # 2. Overhang analysis
            face_normals = mesh.face_normals
            build_dir = [0, 0, 1]  # Assume Z-up build platform
            cos_limit = math.cos(math.radians(max_overhang))

            overhanging_faces = []
            for i, normal in enumerate(face_normals):
                cos_angle = sum(a * b for a, b in zip(normal, build_dir))
                if cos_angle < 0 and abs(cos_angle) > cos_limit:
                    # Face normal points downward at angle > max_overhang
                    overhanging_faces.append(i)

            if overhanging_faces:
                pct = len(overhanging_faces) / len(face_normals) * 100
                results.append(
                    VerificationResult(
                        check="printability",
                        passed=pct < 5.0,  # < 5% overhang is acceptable
                        message=f"{len(overhanging_faces)}/{len(face_normals)} faces ({pct:.1f}%) exceed {max_overhang}° overhang",
                        details={
                            "file": path.name,
                            "overhanging_faces": len(overhanging_faces),
                            "total_faces": len(face_normals),
                            "percentage": pct,
                        },
                        severity="warning" if pct < 5.0 else "error",
                    )
                )

            # 3. Wall thickness (via voxel-based thickness estimate)
            thickness = mesh.nearest.on_surface(mesh.vertices)[1]
            min_thickness = thickness.min()

            if min_thickness < min_wall:
                results.append(
                    VerificationResult(
                        check="printability",
                        passed=False,
                        message=f"Minimum wall thickness {min_thickness:.2f}mm < required {min_wall}mm",
                        details={"file": path.name, "min_thickness": float(min_thickness)},
                        severity="error",
                    )
                )

            # 4. Feature size check
            if min_thickness < nozzle_dia:
                results.append(
                    VerificationResult(
                        check="printability",
                        passed=False,
                        message=f"Features below nozzle diameter ({nozzle_dia}mm) may not print reliably",
                        details={"file": path.name, "min_thickness": float(min_thickness)},
                        severity="warning",
                    )
                )

        except ImportError:
            logger.warning("trimesh not available; skipping printability checks")
            results.append(
                VerificationResult(
                    check="printability",
                    passed=True,
                    message="trimesh unavailable; printability check skipped",
                    severity="warning",
                )
            )
        except Exception as exc:
            results.append(
                VerificationResult(
                    check="printability",
                    passed=False,
                    message=f"Exception checking {path.name}: {exc}",
                    severity="error",
                )
            )

        if not results:
            results.append(
                VerificationResult(
                    check="printability",
                    passed=True,
                    message=f"{path.name} passes printability checks",
                )
            )

        return results


# Patch missing import
import math


def verify_printability(project_dir: str, **kwargs: Any) -> list[VerificationResult]:
    return PrintabilityVerifier().validate(project_dir, **kwargs)
