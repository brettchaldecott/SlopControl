"""Monitor script execution: capture logs, measure resources, detect issues."""

from typing import Any


def capture_logs(stdout: str, stderr: str) -> dict[str, Any]:
    """Parse stdout/stderr for relevant information.

    Returns:
        Dict with 'warnings', 'errors', 'dimensions', etc.
    """
    warnings = [line for line in stderr.splitlines() if "warning" in line.lower()]
    errors = [line for line in stderr.splitlines() if "error" in line.lower()]
    # TODO: Implement more sophisticated log parsing
    return {
        "warnings": warnings,
        "errors": errors,
        "stdout_lines": stdout.splitlines(),
        "stderr_lines": stderr.splitlines(),
    }
