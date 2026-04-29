"""SlopControl — agentic development through plan-controlled verification."""

from .agent import create_agent, run_design_session
from slopcontrol.core.orchestrator import Conductor, PluginRegistry

__version__ = "0.3.0"
__all__ = [
    "create_agent",
    "run_design_session",
    "Conductor",
    "PluginRegistry",
]
