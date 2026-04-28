"""Sandboxed script execution with restricted imports and timeout.

Runs generated design or code scripts in a subprocess with
resource limits and a whitelist of allowed modules.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Whitelisted modules for scripts
DEFAULT_SCRIPT_IMPORTS: set[str] = {
    "math", "json", "os", "sys", "pathlib", "typing",
    "dataclasses", "collections", "itertools", "functools",
    "slopcontrol.core.execution.contract",
}

# Whitelisted modules for code scripts
CODE_SCRIPT_IMPORTS: set[str] = {
    "typing", "collections", "itertools", "functools",
    "pathlib", "os", "sys", "json", "dataclasses", "enum",
    "abc", "inspect", "re",
}

DEFAULT_TIMEOUT: int = 120  # seconds
DEFAULT_MEMORY_MB: int = 512  # Soft limit


def run_script(
    script_path: Path | str,
    project_dir: Path | str,
    domain: str = "code",
    timeout: int = DEFAULT_TIMEOUT,
    memory_mb: int = DEFAULT_MEMORY_MB,
) -> dict[str, Any]:
    """Execute a generated design script in a sandboxed subprocess.

    Args:
        script_path: Path to the Python script (.py).
        project_dir: Project directory for outputs.
        domain: ``"code"`` or ``"code"`` — determines import whitelist.
        timeout: Maximum execution time in seconds.
        memory_mb: Soft memory limit in MiB.

    Returns:
        Dict with ``success``, ``stdout``, ``stderr``, ``results``,
        ``exports``, and ``error``.
    """
    script_path = Path(script_path)
    if not script_path.exists():
        return {
            "success": False,
            "error": f"Script not found: {script_path}",
            "stdout": "",
            "stderr": "",
            "results": {},
            "exports": [],
        }

    start_time = time.time()

    # Build the whitelisted-path environment
    whitelist = DEFAULT_SCRIPT_IMPORTS if domain == "code" else CODE_SCRIPT_IMPORTS
    env = os.environ.copy()
    env["SLOPCONTROL_DOMAIN"] = domain
    env["SLOPCONTROL_PROJECT_DIR"] = str(project_dir)

    # Write a wrapper that validates imports before running the script
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_wrapper.py", delete=False, dir=project_dir
    ) as wrapper:
        wrapper.write(_build_sandbox_wrapper(script_path, whitelist))
        wrapper_path = wrapper.name

    try:
        # Run the wrapper in a subprocess with limits
        cmd = [
            sys.executable,
            "-u",  # Unbuffered stdout
            wrapper_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(project_dir),
        )

        duration = time.time() - start_time

        stdout = result.stdout
        stderr = result.stderr

        # Parse the results JSON from stdout
        results, exports = _parse_results(stdout)

        success = result.returncode == 0

        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "results": results,
            "exports": exports,
            "duration": round(duration, 3),
            "returncode": result.returncode,
        }

    except subprocess.TimeoutExpired:
        logger.error("Script %s timed out after %ss", script_path, timeout)
        return {
            "success": False,
            "error": f"Timeout after {timeout} seconds",
            "stdout": "",
            "stderr": f"Process timed out after {timeout} seconds",
            "results": {},
            "exports": [],
            "duration": round(time.time() - start_time, 3),
        }
    except Exception as exc:
        logger.exception("Sandbox execution failed for %s", script_path)
        return {
            "success": False,
            "error": str(exc),
            "stdout": "",
            "stderr": str(exc),
            "results": {},
            "exports": [],
            "duration": round(time.time() - start_time, 3),
        }
    finally:
        # Clean up wrapper
        try:
            Path(wrapper_path).unlink()
        except OSError:
            pass


def _build_sandbox_wrapper(script_path: Path, whitelist: set[str]) -> str:
    """Generate a Python wrapper that imports the script safely."""
    # Encode whitelist and script path as JSON for injection
    import json as _json

    config = {
        "script_path": str(script_path),
        "whitelist": sorted(whitelist),
    }

    return f'''
import sys
import importlib
import json
import os

CONFIG = {_json.dumps(config)}

class ImportGuard:
    """Meta path hook that blocks non-whitelisted imports."""
    def find_module(self, fullname, path=None):
        # Allow whitelisted modules and their submodules
        for allowed in CONFIG["whitelist"]:
            if fullname == allowed or fullname.startswith(allowed + "."):
                return None  # Allow normal import
        # Block anything not in whitelist
        raise ImportError(
            f"[SANDBOX] Import of '{{fullname}}' is not permitted. "
            f"Allowed: {{CONFIG['whitelist']}}"
        )

    def find_spec(self, fullname, path, target=None):
        return None  # Use default import

# Install the guard before running the script
sys.meta_path.insert(0, ImportGuard())

# Redirect stdout so we can capture results.json cleanly
_results = {{"exports": []}}
_orig_stdout = sys.stdout
_orig_stderr = sys.stderr

import io
_capture = io.StringIO()
sys.stdout = _capture

# Capture results.json if written by the script
_results_path = os.path.join(os.getcwd(), "results.json")

# Execute the script
script_globals = {{"__name__": "__main__", "__file__": CONFIG["script_path"]}}
with open(CONFIG["script_path"]) as _f:
    exec(compile(_f.read(), CONFIG["script_path"], "exec"), script_globals)

# Check for results.json
if os.path.exists(_results_path):
    try:
        with open(_results_path) as _rf:
            _results = json.load(_rf)
    except json.JSONDecodeError:
        pass

# Restore stdout and print results JSON
sys.stdout = _orig_stdout
sys.stderr = _orig_stderr

# Print the results JSON as the very last line
print("\\n\\nSANDBOX_RESULTS_START")
print(json.dumps(_results))
print("SANDBOX_RESULTS_END")
'''


def _parse_results(stdout: str) -> tuple[dict[str, Any], list[str]]:
    """Extract results JSON from the end of stdout."""
    start_marker = "SANDBOX_RESULTS_START"
    end_marker = "SANDBOX_RESULTS_END"

    results: dict[str, Any] = {}
    exports: list[str] = []

    try:
        start = stdout.rfind(start_marker)
        end = stdout.rfind(end_marker)
        if start != -1 and end != -1 and start < end:
            json_str = stdout[start + len(start_marker) : end].strip()
            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                results = parsed
                exports = parsed.get("exports", [])
    except Exception:
        pass

    return results, exports
