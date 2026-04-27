"""Shim for backward-compatible imports.

Re-exports provider registry from the new core location.
"""
from planforge.core.providers.registry import *  # noqa: F401,F403
from planforge.core.providers.registry import get_model, list_available_models  # noqa: F401
from planforge.core.gateway.router import parse_model_string as _parse_base  # noqa: F401


def parse_model_string(model_str: str):
    """Split ``provider:model`` into (provider, model).

    When no colon is present, default provider to ``openai`` for
    backwards compatibility.
    """
    if ":" in model_str:
        return _parse_base(model_str)
    return "openai", model_str.strip()
