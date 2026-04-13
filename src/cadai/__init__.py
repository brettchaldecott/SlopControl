"""CadAI - AI-Powered CAD Agent for Natural Language 3D Modeling"""

from .agent import create_cad_agent
from .tools.cad import CAD_TOOLS
from .tui import run_tui
from .tools.session_manager import SessionManager, DesignState
from .tools.design_history import DesignHistory

__version__ = "0.1.0"
__all__ = [
    "create_cad_agent",
    "CAD_TOOLS",
    "run_tui",
    "SessionManager",
    "DesignState",
    "DesignHistory",
]
