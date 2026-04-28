"""MCP (Model Context Protocol) module for SlopControl.

This module provides MCP server functionality to expose SlopControl CAD tools
to AI clients like Cursor, Claude Desktop, and other MCP-compatible tools.
"""

from .server import SlopControlMCPServer, create_mcp_server, run_server, main
from .tools import CAD_MCP_TOOLS, get_tool_by_name, list_all_tools

__all__ = [
    "SlopControlMCPServer",
    "create_mcp_server",
    "run_server",
    "main",
    "CAD_MCP_TOOLS",
    "get_tool_by_name",
    "list_all_tools",
]
