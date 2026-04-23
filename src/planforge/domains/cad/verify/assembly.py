"""Assembly verification: interference checks, clearance between parts."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from planforge.core.verify.base import DomainVerifier, VerificationResult

logger = logging.getLogger(__name__)


class AssemblyVerifier(DomainVerifier):
    """Verify no part interferes and moving parts have gap."""

    def validate(self, project_dir: str, **kwargs: Any) -> list[VerificationResult]:
        """Check for Boolean intersection between all part pairs."""
        results: list[VerificationResult] = []

        step_files = list(Path(project_dir).glob("exports/*.step"))
        if len(step_files) < 2:
            return [
                VerificationResult(
                    check="assembly",
                    passed=True,
                    message="Single part; no interference check needed",
                )
            ]

        try:
            from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
            from OCP.BRepExtrema import BRepExtrema_DistShapeShape
            from OCP.STEPControl import STEPControl_Reader
            from OCP.IFSelect import IFSelect_RetDone

            # Load all shapes
            shapes: dict[str, Any] = {}
            for step in step_files:
                reader = STEPControl_Reader()
                status = reader.ReadFile(str(step))
                if status == IFSelect_RetDone:
                    reader.TransferRoots()
                    shapes[step.stem] = reader.OneShape()

            names = list(shapes.keys())
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    shape_a = shapes[names[i]]
                    shape_b = shapes[names[j]]

                    # 1. Boolean intersection (clash)
                    common = BRepAlgoAPI_Common(shape_a, shape_b)
                    if common.IsDone():
                        from OCP.BRepGProp import BRepGProp
                        from OCP.GProp import GProp_GProps
                        props = GProp_GProps()
                        BRepGProp.VolumeProperties_s(common.Shape(), props)
                        if props.Mass() > 1e-6:
                            results.append(
                                VerificationResult(
                                    check="assembly",
                                    passed=False,
                                    message=f"Parts '{names[i]}' and '{names[j]}' interfere (volume={props.Mass():.4f} mm³)",
                                    severity="error",
                                    details={"parts": [names[i], names[j]], "overlap_volume": props.Mass()},
                                )
                            )

                    # 2. Minimum distance (clearance)
                    dist = BRepExtrema_DistShapeShape(shape_a, shape_b)
                    if dist.IsDone():
                        min_dist = dist.Value()
                        if min_dist < 0.05:  # 50 µm
                            results.append(
                                VerificationResult(
                                    check="assembly",
                                    passed=False,
                                    message=f"Parts '{names[i]}' and '{names[j]}' too close ({min_dist:.3f}mm)",
                                    severity="warning",
                                    details={"parts": [names[i], names[j]], "distance": min_dist},
                                )
                            )

        except ImportError:
            logger.warning("OCP not available; skipping assembly checks")
            results.append(
                VerificationResult(
                    check="assembly",
                    passed=True,
                    message="OCP unavailable; assembly check skipped",
                    severity="warning",
                )
            )
        except Exception as exc:
            results.append(
                VerificationResult(
                    check="assembly",
                    passed=False,
                    message=f"Assembly check exception: {exc}",
                    severity="error",
                )
            )

        if not results:
            results.append(
                VerificationResult(
                    check="assembly",
                    passed=True,
                    message="No interference detected between parts",
                )
            )

        return results


def verify_assembly(project_dir: str) -> list[VerificationResult]:
    return AssemblyVerifier().validate(project_dir)
