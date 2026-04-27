# PlanForge

**AI-Powered Plan Orchestration for CAD, Software, and Beyond**

[![PyPI version](https://img.shields.io/pypi/v/planforge)](https://pypi.org/project/planforge/)
[![Python](https://img.shields.io/pypi/pyversions/planforge)](https://pypi.org/project/planforge/)
[![License](https://img.shields.io/github/license/yourusername/PlanForge)](LICENSE)

PlanForge is an AI-powered **plan-orchestration engine**. You describe what you want to build in natural language — a 3D part, a Python API, a PCB layout — and PlanForge generates a structured plan, routes each section to the right domain agent, coordinates cross-domain handoffs, and verifies the results.

**The plan is the primary artifact. Everything else is generated from it.**

## Philosophy

Most AI coding assistants treat code, CAD models, and designs as the artifacts to preserve. PlanForge flips this: the **plan** (`plan_forge.md`) is the source of truth. Code, CAD scripts, schematics, and tests are disposable outputs produced by domain-specific agents under the direction of a central Conductor.

This means:
- **Plans are portable** — move them between projects, versions, and teams.
- **Domains are pluggable** — add new expertise areas without rewriting the core.
- **Verification is first-class** — every plan section has corresponding checks.
- **Cross-domain handoffs are explicit** — CAD produces geometry specs that firmware consumes, and the Conductor tracks them.

## Features

- **Plan-First Workflow**: Natural language → structured `plan_forge.md` → executed in steps
- **Multi-Domain Agents**: CAD, software, and more — each with their own tools and verifiers
- **Central Conductor**: Orchestrates step execution, resolves dependencies, manages handoffs
- **Knowledge Base**: RAG-powered context using Qdrant (or brute-force fallback) with RAPTOR hierarchical summaries
- **LLM Gateway**: Unified OpenAI-compatible endpoint with automatic provider fallback (OpenAI, Anthropic, Ollama, custom)
- **Verification Layer**: Domain-specific checks (CAD: geometry, printability, assembly; Code: pytest, mypy, coverage)
- **External Agent Integration**: Dispatch work to OpenCode, Claude, or Cursor adapters
- **MCP Server**: Expose tools to AI clients (Claude Desktop, Cursor, etc.)
- **Version Control**: Automatic git commits for every plan iteration

## Installation

```bash
pip install planforge
```

With optional CAD backends:

```bash
pip install planforge[cad]  # llmcad, build123d, trimesh
```

Or with uv:

```bash
uv add planforge
```

## Quick Start

### 1. Initialize a project

```bash
# Software project
planforge init my-api --domain code

# CAD project
planforge init my-bracket --domain cad

# Multi-domain workspace
planforge init my-robot --multi
```

### 2. Generate a plan

```bash
cd my-api
planforge plan generate --request "Build a FastAPI REST API with CRUD endpoints, pytest tests, and OpenAPI docs"
```

This creates `plan_forge.md` with structured requirements, design decisions, and implementation steps.

### 3. Execute the plan

```bash
planforge orchestrate
```

The Conductor reads the plan, discovers the required domain agent(s), executes each step, and verifies the results.

### 4. Review and iterate

```bash
planforge plan show          # View the current plan
planforge verify --domain code   # Run L3 verification
planforge history            # See git commit history
```

## Domains

PlanForge ships with two mature domains. Adding new ones is straightforward via the `DomainPlugin` interface.

### CAD (`domains/cad/`)

Tools: Box, Cylinder, Sphere, Extrude, Fillet, Chamfer, Shell, Boolean ops (union/cut/intersect), STEP/STL/GLB export, preview rendering.

Verifiers: Geometry validity, assembly interference, mechanical parameters, 3D printability.

```bash
planforge init ducted-fan --domain cad
planforge plan generate --request "Ducted fan assembly, 90mm diameter, 5-blade impeller, PETG-CF printable"
planforge orchestrate
```

### Software (`domains/code/`)

Tools: Read/write/edit code, file operations, test runner (pytest), linter (ruff), type checker (mypy), dependency manager (pip/poetry/uv), git operations.

Verifiers: pytest, mypy, coverage threshold.

```bash
planforge init fastapi-app --domain code
planforge plan generate --request "FastAPI app with SQLite, Pydantic models, and CRUD endpoints"
planforge orchestrate
```

## CLI Commands

```bash
# Project lifecycle
planforge init <name> [--domain cad|code] [--multi]
planforge orchestrate [--resume]

# Plan management
planforge plan create
planforge plan generate --request "..."
planforge plan show
planforge plan update

# Domain execution
planforge execute [--agent planforge|opencode|claude|cursor] [--section N]
planforge verify --domain code|cad

# Legacy (CAD-only sessions still work)
planforge design "Create a 50mm cube"
planforge export bracket --format stl

# Utilities
planforge tools              # List all available tools
planforge models             # List LLM models
planforge history            # Git history
planforge mcp start          # MCP server
planforge gateway start      # LLM gateway
```

## Python API

```python
from planforge import Conductor, PluginRegistry
from planforge.core.plan.renderer import read_plan

# Load a plan
plan = read_plan("./plan_forge.md")

# Create conductor and run
registry = PluginRegistry()
registry.auto_discover()
conductor = Conductor(registry=registry)

result = conductor.run_plan(plan, project_dir="./my-project")
print(f"Success: {result['success']}")
print(f"Artifacts: {len(result['artifacts'])}")
print(f"Handoffs: {len(result['handoffs'])}")
```

## Configuration

Create a `.env` file:

```bash
# LLM credentials
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# PlanForge defaults
PLANFORGE_MODEL=openai:gpt-4o
PLANFORGE_PROJECT_DIR=./projects

# Knowledge base
PLANFORGE_KNOWLEDGE_PATH=~/.planforge/knowledge

# Gateway (optional — runs local OpenAI-compatible proxy)
PLANFORGE_GATEWAY_PORT=8000
PLANFORGE_LLM_CHAIN=openai:gpt-4o,anthropic:claude-sonnet,ollama:llama3
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User / CLI                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────▼───────────────┐
        │     Central Conductor         │
        │  (plan → dispatch → verify)   │
        └───────┬───────────┬───────────┘
                │           │
    ┌───────────▼──────┐   ┌▼───────────────┐
    │  Domain Agents   │   │  Knowledge Base  │
    │  ┌──┐ ┌──┐ ┌──┐ │   │  Qdrant / Brute  │
    │  │CAD│ │SW │ │PCB│ │   │  RAPTOR summaries│
    │  └──┘ └──┘ └──┘ │   └──────────────────┘
    │       .         │
    │    Handoffs     │
    │    (artifacts)   │
    └──────────────────┘
         │         │
    ┌────▼────┐  ┌▼──────┐
    │ Verifiers│  │  KB    │
    │ pytest   │  │ ingest  │
    │ geometry │  │ search  │
    │ coverage │  └─────────┘
    └──────────┘
         │
┌────────▼──────────────────────────────────────────┐
│              LLM Gateway (optional)                 │
│  OpenAI-compatible /v1/chat/completions proxy   │
│   with automatic fallback (kimi, qwen, glm...)   │
└───────────────────────────────────────────────────┘
```

**Components:**

- **Conductor** (`core/orchestrator/`) — reads `plan_forge.md`, selects agents, manages handoffs, checkpoints state
- **Domain Plugins** (`domains/*/plugin.py`) — implement `DomainPlugin`: tools, verifiers, prompts, scaffolding
- **Knowledge** (`core/knowledge/`) — RAG with Qdrant + FastEmbed, RAPTOR hierarchical summaries, brute-force fallback
- **Gateway** (`core/gateway/`) — FastAPI proxy with provider routing and automatic fallback chains
- **Execution Sandbox** (`core/execution/`) — subprocess runner with import whitelisting for untrusted scripts
- **External Adapters** (`integrations/`) — OpenCode, Claude, Cursor subprocess wrappers

## Dependencies

### Core (always installed)
- **deepagents**: Agent framework with planning and filesystem tools
- **langchain**: LLM integration
- **typer**: CLI framework
- **qdrant-client**: Vector DB (falls back to brute-force in-memory if unavailable)
- **gitpython**: Git integration
- **fastapi + uvicorn**: LLM gateway
- **rich + textual**: Terminal UI

### Optional: CAD domain
- **llmcad**: LLM-friendly CAD library
- **build123d**: Parametric CAD built on OpenCASCADE
- **trimesh**: Mesh analysis and verification

### Optional: Code domain
- **pytest + pytest-cov**: Test verification
- **mypy**: Type checking
- **ruff**: Linting

## Documentation

- [Installation](docs/installation.md)
- [Quick Start Guide](docs/quickstart.md)
- [MCP Setup](docs/mcp_setup.md)
- [Design Patterns](docs/design_patterns.md)
- [Example Plans](examples/plan_forge.md)

## Extending PlanForge

Adding a new domain (e.g., PCB design, firmware, hardware verification):

```python
# domains/pcb/plugin.py
from planforge.core.domain_base import DomainPlugin

class PCBPlugin(DomainPlugin):
    name = "pcb"
    display_name = "PCB Design"

    def get_tools(self): ...       # Return LangChain @tool functions
    def get_verifiers(self): ...   # Return DomainVerifier instances
    def get_agent_prompt(self): ...
    def scaffold_project(self, path): ...
    def get_capabilities(self): ...
```

Place it under `planforge/domains/pcb/` and the registry auto-discovers it.

## License

MIT License — see [LICENSE](LICENSE) for details.
