"""Base verification interface for all domain verifiers.

Each domain (CAD, code, etc.) implements a verifier that exposes
``validate()`` and returns structured results.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VerificationResult:
    """Structured result from a single verification check."""

    check: str                      # e.g. "geometry", "mesh", "printability"
    passed: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    severity: str = "info"          # info | warning | error

    def to_log_entry(self) -> dict[str, Any]:
        return {
            "version": self.details.get("version", "1.0"),
            "check": self.check,
            "result": "PASS" if self.passed else "FAIL",
            "notes": self.message,
        }


class DomainVerifier(ABC):
    """Abstract verifier for a specific domain."""

    @abstractmethod
    def validate(self, project_dir: str, **kwargs: Any) -> list[VerificationResult]:
        """Run all verification checks for this domain.

        Returns a list of ``VerificationResult`` objects.
        """
        ...
