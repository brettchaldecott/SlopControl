"""Contract that generated scripts must follow.

Scripts import this module and call ``record()`` so the sandbox
knows what files were produced.
"""

import json
import os
from pathlib import Path
from typing import Any


RESULTS_FILE = "results.json"
_artifacts: list[dict[str, Any]] = []


def record(path: str, kind: str = "file", metadata: dict | None = None) -> None:
    """Record a produced file for the sandbox.

    Args:
        path: File path produced by the script.
        kind: Type of artifact (file, module, test, etc.).
        metadata: Optional dict (lines, language, etc.).
    """
    entry = {
        "path": path,
        "kind": kind,
        "format": Path(path).suffix.lstrip(".") if "." in Path(path).name else "",
        "metadata": metadata or {},
    }
    _artifacts.append(entry)
    _flush_results()


def _flush_results() -> None:
    """Write accumulated artifacts to ``results.json``."""
    results = {"artifacts": _artifacts}
    # Write to current working directory (the project dir in sandbox)
    out = Path.cwd() / RESULTS_FILE
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
