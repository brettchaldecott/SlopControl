"""MCP Server for SlopControl.

This module provides an MCP (Model Context Protocol) server implementation
that exposes SlopControl CAD tools to AI clients like Cursor, Claude Desktop, etc.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    from mcp.server.stdio import stdio_server

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

import structlog

from slopcontrol.domains.cad.tools.cad import CAD_TOOLS
from slopcontrol.domains.cad.tools.visualization import VISUALIZATION_TOOLS
from slopcontrol.domains.cad.tools.git_ops import GIT_TOOLS
from slopcontrol.domains.cad.tools.file_ops import FILE_OPS_TOOLS
from .tools import get_tool_by_name, list_all_tools

logger = structlog.get_logger()


ALL_TOOLS = CAD_TOOLS + VISUALIZATION_TOOLS + GIT_TOOLS + FILE_OPS_TOOLS


class SlopControlMCPServer:
    """MCP Server for SlopControl CAD tools."""

    def __init__(self, name: str = "slopcontrol"):
        """Initialize the MCP server.

        Args:
            name: Server name
        """
        if not MCP_AVAILABLE:
            raise ImportError("MCP is required for server mode. Install with: pip install mcp")

        self.name = name
        self.server = Server(self.name)
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP request handlers."""
        from mcp.server import Server
        from mcp.types import (
            ListToolsRequest,
            ListToolsResult,
            CallToolRequest,
            CallToolResult,
            Tool,
        )

        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """Handle list_tools request."""
            tools = []
            for tool_func in ALL_TOOLS:
                schema = tool_func.args_schema
                param_schema = {}

                if schema:
                    try:
                        param_schema = schema.model_json_schema()
                    except Exception:
                        param_schema = {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        }

                tools.append(
                    Tool(
                        name=tool_func.name,
                        description=tool_func.description or "",
                        inputSchema=param_schema,
                    )
                )

            return ListToolsResult(tools=tools)

        @self.server.call_tool()
        async def call_tool(
            name: str,
            arguments: dict[str, Any],
        ) -> CallToolResult:
            """Handle call_tool request."""
            tool = get_tool_by_name(name)

            if not tool:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Tool not found: {name}")],
                    isError=True,
                )

            try:
                result = await asyncio.coroutine(tool.invoke)(arguments)
                return CallToolResult(content=[TextContent(type="text", text=str(result))])
            except Exception as e:
                logger.error("Tool execution failed", tool=name, error=str(e))
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True,
                )

    async def run(self, transport: str = "stdio"):
        """Run the MCP server.

        Args:
            transport: Transport type ('stdio' or 'sse')
        """
        if transport == "stdio":
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )
        else:
            raise ValueError(f"Unsupported transport: {transport}")


def create_mcp_server() -> SlopControlMCPServer:
    """Create an MCP server instance.

    Returns:
        Configured SlopControlMCPServer instance
    """
    return SlopControlMCPServer()


async def run_server(transport: str = "stdio", port: Optional[int] = None):
    """Run the MCP server.

    Args:
        transport: Transport type ('stdio' or 'sse')
        port: Port for SSE transport (optional)
    """
    server = create_mcp_server()
    await server.run(transport=transport)


def main():
    """Main entry point for MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="SlopControl MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport type (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port for SSE transport",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.debug:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    if not MCP_AVAILABLE:
        print("Error: MCP is not installed. Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)

    asyncio.run(run_server(transport=args.transport, port=args.port))


if __name__ == "__main__":
    main()
