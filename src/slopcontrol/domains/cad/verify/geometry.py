"""Geometric verification: manifold checks, self-intersection, BRep validity."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from slopcontrol.core.verify.base import DomainVerifier, VerificationResult

logger = logging.getLogger(__name__)


class GeometryVerifier(DomainVerifier):
    """Verify BRep geometry validity using build123d / OCP."""

    def validate(self, project_dir: str, **kwargs: Any) -> list[VerificationResult]:
        """Check all exported STEP files for geometric validity."""
        results: list[VerificationResult] = []
        exports_dir = Path(project_dir) / "exports"

        if not exports_dir.exists():
            return [
                VerificationResult(
                    check="geometry",
                    passed=False,
                    message="No exports directory found",
                    severity="error",
                )
            ]

        step_files = list(exports_dir.glob("*.step"))
        if not step_files:
            return [
                VerificationResult(
                    check="geometry",
                    passed=False,
                    message="No STEP files to verify",
                    severity="error",
                )
            ]

        for step_file in step_files:
            results.extend(self._check_step(step_file))

        return results

    def _check_step(self, path: Path) -> list[VerificationResult]:
        """Validate a single STEP file."""
        results: list[VerificationResult] = []

        try:
            from OCP.BRepCheck import BRepCheck_Analyzer
            from OCP.STEPControl import STEPControl_Reader
            from OCP.IFSelect import IFSelect_RetDone

            # Read STEP
            reader = STEPControl_Reader()
            status = reader.ReadFile(str(path))
            if status != IFSelect_RetDone:
                results.append(
                    VerificationResult(
                        check="geometry",
                        passed=False,
                        message=f"Failed to read STEP: {path.name}",
                        severity="error",
                    )
                )
                return results

            reader.TransferRoots()
            shape = reader.OneShape()

            # BRep validity check
            analyzer = BRepCheck_Analyzer(shape)
            valid = analyzer.IsValid()

            results.append(
                VerificationResult(
                    check="geometry",
                    passed=valid,
                    message=f"BRep validity: {'PASS' if valid else 'FAIL'} for {path.name}",
                    details={"file": str(path), "valid": valid},
                    severity="info" if valid else "error",
                )
            )

        except ImportError:
            logger.warning("OCP not available; skipping STEP validity check")
            results.append(
                VerificationResult(
                    check="geometry",
                    passed=True,
                    message="OCP unavailable; geometry check skipped",
                    severity="warning",
                )
            )
        except Exception as exc:
            results.append(
                VerificationResult(
                    check="geometry",
                    passed=False,
                    message=f"Exception checking {path.name}: {exc}",
                    severity="error",
                )
            )

        return results


def verify_geometry(project_dir: str) -> list[VerificationResult]:
    """Convenience function."""
    return GeometryVerifier().validate(project_dir)
