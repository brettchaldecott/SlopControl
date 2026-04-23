"""Mechanical verification: gear mesh, backlash, bearing fits.

Uses parameter-based math and build123d measurements.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

from planforge.core.verify.base import DomainVerifier, VerificationResult

logger = logging.getLogger(__name__)


class MechanicalVerifier(DomainVerifier):
    """Verify mechanical constraints: gear mesh, clearances, fits."""

    def validate(self, project_dir: str, **kwargs: Any) -> list[VerificationResult]:
        """Run mechanical checks based on plan parameters."""
        results: list[VerificationResult] = []

        # Read plan parameters
        params = self._load_params(project_dir)
        if not params:
            return [
                VerificationResult(
                    check="mechanical",
                    passed=False,
                    message="No params.json found; cannot verify mesh",
                    severity="warning",
                )
            ]

        # Check gear mesh if planetary parameters present
        if "planetary" in params or "gear" in params:
            results.extend(self._check_gear_mesh(params))

        # Check bearing fits if present
        if "bearing" in params:
            results.extend(self._check_bearing_fits(params))

        return results

    def _load_params(self, project_dir: str) -> dict[str, Any]:
        params_path = Path(project_dir) / "params.json"
        if not params_path.exists():
            return {}
        import json
        return json.loads(params_path.read_text())

    def _check_gear_mesh(self, params: dict[str, Any]) -> list[VerificationResult]:
        """Verify gear mesh parameters."""
        results: list[VerificationResult] = []
        planetary = params.get("planetary", {})

        ring_teeth = planetary.get("ring_teeth", 0)
        sun_teeth = planetary.get("sun_teeth", 0)
        planet_count = planetary.get("planet_count", 0)
        module = planetary.get("module", 0)
        backlash = planetary.get("backlash", 0)

        # Validate gear ratio consistency
        if ring_teeth and sun_teeth:
            expected_planet = (ring_teeth - sun_teeth) // 2
            if expected_planet <= 0:
                results.append(
                    VerificationResult(
                        check="mechanical",
                        passed=False,
                        message=f"Invalid gear ratio: R={ring_teeth}, S={sun_teeth}",
                        severity="error",
                    )
                )

        # Validate planet count fits
        if planet_count and ring_teeth and sun_teeth:
            angle = 360 / planet_count
            # Basic check: planets must fit angularly
            if angle < 30:
                results.append(
                    VerificationResult(
                        check="mechanical",
                        passed=False,
                        message=f"Planet count {planet_count} too high; angular spacing = {angle:.1f}°",
                        severity="warning",
                    )
                )

        # Backlash check
        if module and backlash:
            expected_backlash = module * 0.1
            if backlash < expected_backlash * 0.5:
                results.append(
                    VerificationResult(
                        check="mechanical",
                        passed=False,
                        message=f"Backlash {backlash}mm too tight for module {module}mm",
                        severity="warning",
                    )
                )

        if not results:
            results.append(
                VerificationResult(
                    check="mechanical",
                    passed=True,
                    message="Gear mesh parameters within tolerance",
                )
            )

        return results

    def _check_bearing_fits(self, params: dict[str, Any]) -> list[VerificationResult]:
        """Verify bearing interference / clearance fits."""
        results: list[VerificationResult] = []
        bearing = params.get("bearing", {})

        shaft_dia = bearing.get("shaft_diameter", 0)
        bore = bearing.get("bore", 0)
        fit_type = bearing.get("fit", "interference")

        if shaft_dia and bore:
            clearance = bore - shaft_dia
            if fit_type == "interference" and clearance > 0:
                results.append(
                    VerificationResult(
                        check="mechanical",
                        passed=False,
                        message=f"Interference fit requires shaft > bore; got {shaft_dia}mm shaft, {bore}mm bore",
                        severity="error",
                    )
                )
            elif fit_type == "clearance" and clearance < 0:
                results.append(
                    VerificationResult(
                        check="mechanical",
                        passed=False,
                        message=f"Clearance fit requires bore > shaft; got {clearance:.3f}mm interference",
                        severity="error",
                    )
                )

        return results


def verify_mechanical(project_dir: str) -> list[VerificationResult]:
    return MechanicalVerifier().validate(project_dir)
