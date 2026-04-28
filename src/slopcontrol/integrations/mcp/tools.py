"""MCP server tools for SlopControl.

This module provides MCP (Model Context Protocol) tool definitions
for the CAD tools, allowing AI clients to use SlopControl as a tool server.
"""

from typing import Any, Optional

from slopcontrol.domains.cad.tools.cad import CAD_TOOLS
from slopcontrol.domains.cad.tools.visualization import VISUALIZATION_TOOLS
from slopcontrol.domains.cad.tools.git_ops import GIT_TOOLS
from slopcontrol.domains.cad.tools.file_ops import FILE_OPS_TOOLS


CAD_MCP_TOOLS = CAD_TOOLS + VISUALIZATION_TOOLS + GIT_TOOLS + FILE_OPS_TOOLS


def get_tool_by_name(name: str):
    """Get a tool by its name.

    Args:
        name: Name of the tool

    Returns:
        Tool function or None if not found
    """
    for tool in CAD_MCP_TOOLS:
        if tool.name == name:
            return tool
    return None


def list_all_tools() -> list[dict[str, Any]]:
    """List all available MCP tools with their schemas.

    Returns:
        List of tool definitions with names and descriptions
    """
    tools = []
    for tool_func in CAD_MCP_TOOLS:
        schema = tool_func.args_schema
        tools.append(
            {
                "name": tool_func.name,
                "description": tool_func.description,
                "parameters": schema.model_json_schema() if schema else {},
            }
        )
    return tools
