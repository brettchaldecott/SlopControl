"""Python pytest verification for software domain."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from slopcontrol.core.verify.base import DomainVerifier, VerificationResult

logger = logging.getLogger(__name__)


class PytestVerifier(DomainVerifier):
    """Run pytest and parse the results."""

    def validate(self, project_dir: str, **kwargs: Any) -> list[VerificationResult]:
        cmd = [sys.executable, "-m", "pytest", "-q", "--tb=short", project_dir]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            passed = result.returncode == 0
            lines = result.stdout.splitlines()
            summary = lines[-1] if lines else "no output"
            return [
                VerificationResult(
                    check="pytest",
                    passed=passed,
                    message=summary,
                    details={"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr},
                    severity="info" if passed else "error",
                )
            ]
        except FileNotFoundError:
            return [
                VerificationResult(
                    check="pytest",
                    passed=False,
                    message="pytest not installed",
                    severity="error",
                )
            ]
        except Exception as exc:
            return [
                VerificationResult(
                    check="pytest", passed=False, message=str(exc), severity="error"
                )
            ]
