# PlanForge

**AI-Powered CAD Agent for Natural Language 3D Modeling**

[![PyPI version](https://img.shields.io/pypi/v/cadAI)](https://pypi.org/project/cadAI/)
[![Python](https://img.shields.io/pypi/pyversions/cadAI)](https://pypi.org/project/cadAI/)
[![License](https://img.shields.io/github/license/yourusername/PlanForge)](LICENSE)

PlanForge is an AI-powered CAD agent that enables you to design complex 3D parts using natural language. Built on [deepagents](https://github.com/langchain-ai/deepagents) and [llmcad](https://llmcad.org/), it provides an iterative design workflow with visual feedback.

## Features

- **Natural Language Design**: Describe what you want in plain English
- **Iterative Workflow**: Refine designs based on visual feedback
- **Multiple Export Formats**: STEP, STL, and GLB output
- **Version Control**: Automatic git commits for design history
- **MCP Server**: Expose CAD tools to AI clients (Cursor, Claude Desktop)
- **Multi-Provider Support**: OpenAI, Anthropic, Ollama

## Installation

```bash
pip install cadAI
```

Or with uv:

```bash
uv add cadAI
```

## Quick Start

### 1. Initialize a project

```bash
planforge init my-design
cd my-design
```

### 2. Run a design session

```bash
planforge design "Create a U-shaped mounting bracket with 4 mounting holes"
```

### 3. Iterate based on feedback

```
User: "Make the holes 6mm instead of 5mm"
Agent: [Updates design and shows preview]
```

### 4. Export your design

```bash
planforge export bracket --format stl
```

## Usage

### CLI Commands

```bash
# Initialize a new project
planforge init my-project

# Run a design session
planforge design "Create a gear with 12 teeth"

# Export a design
planforge export gear --format step

# View design history
planforge history

# List available models
planforge models
```

### Python API

```python
from planforge import create_cad_agent

agent = create_cad_agent(
    model="openai:gpt-4o",
    project_dir="./projects",
)

result = agent.invoke({
    "messages": [("user", "Create a 50mm cube with a 10mm hole through it")]
})
```

## Configuration

Create a `.env` file:

```bash
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
PLANFORGE_MODEL=openai:gpt-4o
PLANFORGE_PROJECT_DIR=./projects
```

## MCP Server

PlanForge can run as an MCP server, exposing CAD tools to AI coding assistants:

```bash
planforge mcp start
```

See [docs/mcp_setup.md](docs/mcp_setup.md) for configuration with Cursor and Claude Desktop.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         PlanForge                               │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │  Planning   │  │   Memory     │  │   CAD Skills      │ │
│  │  (write_    │  │  (AGENTS.md) │  │   (progressive     │ │
│  │   todos)    │  │              │  │    disclosure)     │ │
│  └──────┬──────┘  └──────┬───────┘  └─────────┬──────────┘ │
│         │                 │                    │             │
│  ┌──────▼──────────────────────────────────────▼──────────┐ │
│  │               Tool Layer                               │ │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────────┐  │ │
│  │  │ llmcad     │ │ Git Ops    │ │ Visualization     │  │ │
│  │  │ Tools      │ │            │ │ (snapshots)      │  │ │
│  └──────────────┴─┴────────────┴─┴──────────────────┘  │ │
│  ┌──────────────────────────────────────────────────────┐  │
│  │               LLM Provider Layer                     │  │
│  │   OpenAI │ Anthropic │ Ollama │ LM Studio │ etc.    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Dependencies

- **deepagents**: Agent framework with planning and filesystem tools
- **llmcad**: LLM-friendly CAD library built on OpenCASCADE
- **langchain**: LLM integration
- **typer**: CLI framework
- **gitpython**: Git integration for version control

## Documentation

- [Installation](docs/installation.md)
- [Quick Start Guide](docs/quickstart.md)
- [MCP Setup](docs/mcp_setup.md)
- [Design Patterns](docs/design_patterns.md)

## License

MIT License - see [LICENSE](LICENSE) for details.
