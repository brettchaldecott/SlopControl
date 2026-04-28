"""Contract that generated design scripts must follow.

Scripts import this module and call ``export()`` so the sandbox
knows what geometry was produced.
"""

import json
import os
from pathlib import Path
from typing import Any


RESULTS_FILE = "results.json"
_exports: list[dict[str, Any]] = []


def export(body: Any, path: str, metadata: dict | None = None) -> None:
    """Export a body and record metadata for the sandbox.

    Args:
        body: build123d Part or similar geometry object.
        path: Export file path (.step, .stl, or .glb).
        metadata: Optional dict (dimensions, volume, etc.).
    """
    import json

    entry = {
        "path": path,
        "format": Path(path).suffix.lstrip("."),
        "metadata": metadata or {},
    }
    _exports.append(entry)
    _flush_results()


def _flush_results() -> None:
    """Write accumulated exports to ``results.json``."""
    results = {"exports": _exports}
    # Write to current working directory (the project dir in sandbox)
    out = Path.cwd() / RESULTS_FILE
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
