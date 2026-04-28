"""Shim for backward-compatible imports.

Re-exports CAD helpers from the new domains location.
"""
from slopcontrol.domains.cad.utils.cad_helpers import *  # noqa: F401,F403
from slopcontrol.domains.cad.utils.cad_helpers import serialize_body, deserialize_body, get_model_info, validate_dimensions  # noqa: F401
