# MCP Setup Guide

SlopControl can run as an MCP (Model Context Protocol) server, exposing software development tools to AI coding assistants like Cursor, Claude Desktop, and other MCP-compatible clients.

## What is MCP?

MCP (Model Context Protocol) is a standard protocol that allows AI models to use external tools. By running SlopControl as an MCP server, AI clients can access code editing, testing, and verification tools directly.

## Starting the MCP Server

### Basic Usage (stdio mode)

```bash
slopcontrol mcp start
```

This starts the server using stdio transport, which works with most AI clients.

### SSE Mode (for web clients)

```bash
slopcontrol mcp start --transport sse --port 8765
```

### Check Status

```bash
slopcontrol mcp status
```

## Client Configuration

### Cursor

Add to your Cursor settings (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "slopcontrol": {
      "command": "slopcontrol",
      "args": ["mcp", "start"]
    }
  }
}
```

Or use npx:

```json
{
  "mcpServers": {
    "slopcontrol": {
      "command": "npx",
      "args": ["-y", "slopcontrol", "mcp", "start"]
    }
  }
}
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "slopcontrol": {
      "command": "slopcontrol",
      "args": ["mcp", "start"],
      "env": {
        "GROK_API_KEY": "your-api-key"
      }
    }
  }
}
```

### VS Code Copilot

MCP support in VS Code Copilot is available in the latest versions. Add to your VS Code settings:

```json
{
  "mcp.servers": {
    "slopcontrol": {
      "command": "slopcontrol",
      "args": ["mcp", "start"]
    }
  }
}
```

## Available Tools

Once connected, the following tools are available:

### File Operations
- `read_code` — Read a file
- `write_code` — Write a file
- `edit_code` — Edit a file in-place
- `delete_file` — Delete a file
- `list_files` — List files in a directory
- `find_in_files` — Search for text across files

### Code Quality
- `run_tests` — Run pytest
- `run_linter` — Run ruff
- `run_type_check` — Run mypy

### Dependencies
- `add_dependency` — Add a package dependency
- `remove_dependency` — Remove a package dependency
- `list_dependencies` — List installed dependencies

### Git
- `init_git_repo` — Initialize a git repository
- `commit` — Commit changes
- `get_history` — View commit history
- `create_branch` — Create a git branch
- `merge_branch` — Merge a branch

## Example Usage

After connecting, you can use tools in your AI conversations:

```
You: Create a FastAPI app with a single /health endpoint

AI: I'll create a FastAPI app:
1. write_code(path="src/main.py", content="from fastapi import FastAPI...")
2. run_tests() → All tests pass

Done! The FastAPI app has been created at src/main.py.
```

## Troubleshooting

### Server won't start

Check that SlopControl is installed:
```bash
slopcontrol --version
```

### Client can't connect

- Ensure the server is running before starting your AI client
- Check that the command path is correct in your config
- For stdio mode, ensure your client supports stdio transport

### API key errors

Set your API keys as environment variables:
```bash
export GROK_API_KEY=your-key
slopcontrol mcp start
```

Or include them in your client config:
```json
{
  "mcpServers": {
    "slopcontrol": {
      "command": "slopcontrol",
      "args": ["mcp", "start"],
      "env": {
        "GROK_API_KEY": "your-key"
      }
    }
  }
}
```
