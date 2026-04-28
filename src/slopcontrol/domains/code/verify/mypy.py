"""Python mypy verification for software domain."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from slopcontrol.core.verify.base import DomainVerifier, VerificationResult

logger = logging.getLogger(__name__)


class MypyVerifier(DomainVerifier):
    """Run mypy and return type-check results."""

    def validate(self, project_dir: str, **kwargs: Any) -> list[VerificationResult]:
        cmd = [sys.executable, "-m", "mypy", "--ignore-missing-imports", project_dir]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            passed = result.returncode == 0
            return [
                VerificationResult(
                    check="mypy",
                    passed=passed,
                    message="Mypy passed" if passed else result.stdout.splitlines()[-1],
                    details={"returncode": result.returncode},
                    severity="info" if passed else "warning",
                )
            ]
        except FileNotFoundError:
            return [
                VerificationResult(
                    check="mypy",
                    passed=False,
                    message="mypy not installed",
                    severity="error",
                )
            ]
        except Exception as exc:
            return [
                VerificationResult(
                    check="mypy", passed=False, message=str(exc), severity="error"
                )
            ]
