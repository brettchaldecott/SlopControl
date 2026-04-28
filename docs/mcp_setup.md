# MCP Setup Guide

SlopControl can run as an MCP (Model Context Protocol) server, exposing CAD tools to AI coding assistants like Cursor, Claude Desktop, and other MCP-compatible clients.

## What is MCP?

MCP (Model Context Protocol) is a standard protocol that allows AI models to use external tools. By running SlopControl as an MCP server, AI clients can access CAD tools directly.

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
        "OPENAI_API_KEY": "your-api-key"
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

### Shapes
- `create_box` - Create a 3D box
- `create_cylinder` - Create a 3D cylinder
- `create_sphere` - Create a 3D sphere

### Sketches
- `create_rect` - Create a rectangular sketch
- `create_circle` - Create a circular sketch
- `create_ellipse` - Create an elliptical sketch
- `create_polygon` - Create a polygon sketch

### Operations
- `extrude_sketch` - Extrude a sketch to 3D
- `revolve_sketch` - Revolve a sketch
- `add_fillet` - Add fillet to edges
- `add_chamfer` - Add chamfer to edges
- `create_shell` - Create a shell/hollow body
- `mirror_body` - Mirror a body

### Booleans
- `union_bodies` - Combine two bodies
- `cut_body` - Subtract one body from another
- `intersect_bodies` - Keep only overlapping volume

### Export
- `export_model` - Export to STEP, STL, or GLB
- `get_body_info` - Get model dimensions and properties

### Visualization
- `render_preview` - Render a preview image
- `display_preview` - Display preview in terminal
- `get_model_info_detailed` - Get detailed model info

### Git
- `commit_design` - Commit current design
- `get_design_history` - View version history
- `restore_version` - Restore to previous version

## Example Usage

After connecting, you can use CAD tools in your AI conversations:

```
You: Create a 50mm cube and export it as STL

AI: I'll create a 50mm cube and export it:
1. create_box(width=50, height=50, depth=50, name="cube")
2. export_model(body_data=..., format="stl", path="cube.stl")

Done! The cube has been created and exported to cube.stl.
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
export OPENAI_API_KEY=your-key
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
        "OPENAI_API_KEY": "your-key"
      }
    }
  }
}
```
