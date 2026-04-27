"""Shim for backward-compatible imports.

Re-exports CAD tools from the new domains location.
"""
from planforge.domains.cad.tools.cad import *  # noqa: F401,F403
from planforge.domains.cad.tools.cad import CAD_TOOLS  # noqa: F401
