"""MCP (Model Context Protocol) module for CadAI.

This module provides MCP server functionality to expose CadAI CAD tools
to AI clients like Cursor, Claude Desktop, and other MCP-compatible tools.
"""

from .server import CadAIMCPServer, create_mcp_server, run_server, main
from .tools import CAD_MCP_TOOLS, get_tool_by_name, list_all_tools

__all__ = [
    "CadAIMCPServer",
    "create_mcp_server",
    "run_server",
    "main",
    "CAD_MCP_TOOLS",
    "get_tool_by_name",
    "list_all_tools",
]
