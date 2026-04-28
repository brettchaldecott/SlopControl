"""MCP server tools for SlopControl.

Provides MCP (Model Context Protocol) tool definitions for the code domain,
allowing AI clients to use SlopControl as a tool server for software development.
"""

from typing import Any, Optional

from slopcontrol.domains.code.tools.code import CODE_TOOLS
from slopcontrol.domains.code.tools.file_ops import FILE_TOOLS
from slopcontrol.domains.code.tools.git_ops import GIT_TOOLS
from slopcontrol.domains.code.tools.test_runner import TEST_TOOLS
from slopcontrol.domains.code.tools.dependency_manager import DEP_TOOLS


MCP_TOOLS = CODE_TOOLS + FILE_TOOLS + GIT_TOOLS + TEST_TOOLS + DEP_TOOLS


def get_tool_by_name(name: str):
    """Get a tool by its name.

    Args:
        name: Name of the tool

    Returns:
        Tool function or None if not found
    """
    for tool in MCP_TOOLS:
        if tool.name == name:
            return tool
    return None


def list_all_tools() -> list[dict[str, Any]]:
    """List all available MCP tools with their schemas.

    Returns:
        List of tool definitions with names and descriptions
    """
    tools = []
    for tool_func in MCP_TOOLS:
        schema = tool_func.args_schema
        tools.append(
            {
                "name": tool_func.name,
                "description": tool_func.description,
                "parameters": schema.model_json_schema() if schema else {},
            }
        )
    return tools
