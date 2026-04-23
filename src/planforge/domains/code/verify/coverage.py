"""Python coverage verification for software domain."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from planforge.core.verify.base import DomainVerifier, VerificationResult

logger = logging.getLogger(__name__)


class CoverageVerifier(DomainVerifier):
    """Run pytest-cov and verify threshold."""

    def validate(self, project_dir: str, **kwargs: Any) -> list[VerificationResult]:
        threshold = kwargs.get("threshold", 80)
        cmd = [sys.executable, "-m", "pytest", "--cov-report=term-missing", "--cov=" + str(project_dir), "-q", project_dir]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            # Coverage % appears in the last line
            lines = result.stdout.splitlines()
            percent = 0.0
            for line in reversed(lines):
                if "%" in line and "coverage" in line.lower():
                    # Parse the percentage
                    import re
                    match = re.search(r'(\d+(?:\.\d+)?)%', line)
                    if match:
                        percent = float(match.group(1))
                        break
            passed = percent >= threshold
            return [
                VerificationResult(
                    check="coverage",
                    passed=passed,
                    message=f"Coverage: {percent:.1f}% (threshold: {threshold}%)",
                    details={"percent": percent, "threshold": threshold},
                    severity="info" if passed else "error",
                )
            ]
        except FileNotFoundError:
            return [
                VerificationResult(
                    check="coverage",
                    passed=False,
                    message="pytest-cov not installed",
                    severity="error",
                )
            ]
        except Exception as exc:
            return [
                VerificationResult(
                    check="coverage", passed=False, message=str(exc), severity="error"
                )
            ]
