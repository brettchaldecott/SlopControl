# SlopControl

**Agentic Development Through Plan-Controlled Verification**

[![PyPI version](https://img.shields.io/pypi/v/slopcontrol)](https://pypi.org/project/slopcontrol/)
[![Python](https://img.shields.io/pypi/pyversions/slopcontrol)](https://pypi.org/project/slopcontrol/)
[![License](https://img.shields.io/github/license/brettchaldecott/SlopControl)](LICENSE)

SlopControl is an **agentic development system**. It treats AI-generated code, models, and designs as disposable slop — controlled and refined through structured plans, empirical verification, and competing agent tournaments.

**The plan (`slop_control.md`) is the source of truth. Everything else is ephemeral.**

## Philosophy

Most AI coding assistants treat generated code as sacred. SlopControl flips this: the **plan** is durable; the outputs are slop to be iterated, verified, and discarded until they pass.

- **Plans are portable** — move them between models, domains, and teams.
- **Domains are pluggable** — CAD, software, PCB, firmware — each via `DomainPlugin`.
- **Verification is first-class** — every section has checks (pytest, mypy, geometry, printability).
- **Agents compete empirically** — run multiple candidates per step, let verifiers pick the winner.
- **Cost is tracked** — daily budgets prevent runaway API spend.
- **Truth accumulates** — historical performance per (task, agent, model) guides future selections.

## What SlopControl Is NOT

- ❌ Not a CAD tool. CAD is one domain plugin among many.
- ❌ Not a chat interface. It's an orchestration engine with structured plans.
- ❌ Not trusting. Every output is verified before acceptance.

## Features

- **Plan-First Workflow**: Natural language → `slop_control.md` → executed in verified steps
- **Central Conductor**: Reads plans, dispatches to domain agents, coordinates handoffs
- **Parallel Competition**: Multiple agent candidates per step — verifier picks winner (`--compete`)
- **Cost Tracking**: Daily budget caps with historical spend logging
- **Truth Database**: Empirical performance records per task/agent/model
- **Knowledge Base**: RAG with Qdrant + RAPTOR hierarchical summaries
- **LLM Gateway**: OpenAI-compatible proxy with automatic fallback (Grok, OpenAI, Ollama, local)
- **Local Model Discovery**: Auto-probes LM Studio, vLLM, llama.cpp on startup
- **Cross-Domain Handoffs**: CAD geometry specs → firmware parameters, tracked explicitly
- **MCP Server**: Expose tools to Claude Desktop, Cursor, OpenCode

## Installation

```bash
pip install slopcontrol
```

With CAD support (optional):

```bash
pip install slopcontrol[cad]  # llmcad, build123d, trimesh
```

Or with uv:

```bash
uv add slopcontrol
```

## Quick Start — Software

```bash
# 1. Create project
slopcontrol init my-api --domain code

# 2. Generate plan
cd my-api
slopcontrol plan generate --request "Build a FastAPI REST API with CRUD, SQLite, Pydantic, and pytest"

# 3. Execute with competition (multiple agents, verifier picks winner)
slopcontrol orchestrate --compete --budget 5.00

# 4. Verify
slopcontrol verify --domain code
```

## Quick Start — CAD

```bash
slopcontrol init bracket --domain cad
slopcontrol plan generate --request "Ducted fan, 90mm, 5-blade, PETG-CF printable"
slopcontrol orchestrate
slopcontrol verify --domain cad
```

## CLI Commands

```bash
# Core workflow
slopcontrol init <name> [--domain code|cad] [--multi]
slopcontrol plan generate --request "..."
slopcontrol orchestrate [--compete] [--budget 5.0] [--compete-agents planforge,opencode]
slopcontrol verify --domain code|cad

# Infrastructure
slopcontrol gateway start    # LLM proxy with fallback
slopcontrol mcp start        # MCP tool server
slopcontrol list-models      # Available LLM models

# Utilities
slopcontrol tui              # Interactive terminal UI
slopcontrol plan show        # View current plan
```

### Competition Mode

```bash
# Run 3 parallel agents per step, verifier picks winner
slopcontrol orchestrate --compete --compete-agents planforge,opencode

# Budget-limited competition
slopcontrol orchestrate --compete --budget 2.00 --compete-judge hybrid
```

## Configuration

`.env` file:

```bash
# LLM credentials
GROK_API_KEY=xai-...
OPENAI_API_KEY=sk-...

# Defaults
SLOPCONTROL_MODEL=grok:grok-3-beta
SLOPCONTROL_PROJECT_DIR=./projects
SLOPCONTROL_GATEWAY_PORT=8000
SLOPCONTROL_LLM_CHAIN=grok:grok-3-beta,openai:gpt-4o,ollama:llama3

# Budget control
SLOPCONTROL_DAILY_BUDGET=5.0

# Local model preference
SLOPCONTROL_PREFER_LOCAL=true
```

## Domains

| Domain | Tools | Verifiers |
|---|---|---|
| **code** | read/write/edit, pytest, ruff, mypy, pip/poetry/uv, git | pytest, mypy, coverage |
| **cad** | box, cylinder, sphere, boolean ops, STEP/STL/GLB export, preview | geometry, assembly, mechanical, printability |

Add new domains by implementing `DomainPlugin` in `domains/<name>/plugin.py`.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      User / CLI                          │
└───────────────────────┬──────────────────────────────────┘
                        │
        ┌───────────────▼──────────────┐
        │    Central Conductor         │
        │  plan → budget → compete →   │
        │   verify → truth → persist     │
        └───────┬──────────┬───────────┘
                │          │
    ┌───────────▼──────┐  ┌▼──────────────┐
    │  Domain Agents   │  │  Truth DB     │
    │  ┌──┐ ┌──┐ ┌──┐ │  │  (KB records) │
    │  │SW│ │CAD│ │PCB│ │  └──────────────┘
    │  └──┘ └──┘ └──┘ │
    │    Competition   │        ┌──────────┐
    │    (parallel)   │        │ Verifiers│
    └──────────────────┘        │pytest    │
         │         │           │geometry  │
    ┌────▼────┐  ┌▼──────┐    │coverage  │
    │ Cost    │  │KB     │    └──────────┘
    │ Tracker │  │RAG    │
    └─────────┘  └───────┘
         │
┌────────▼────────────────────────────────────────┐
│          LLM Gateway (optional)                  │
│  OpenAI-compatible /v1/chat/completions         │
│  Fallback: grok → openai → ollama → local       │
└──────────────────────────────────────────────────┘
```

## Python API

```python
from slopcontrol import Conductor, PluginRegistry
from slopcontrol.core.plan.renderer import read_plan

plan = read_plan("./slop_control.md")
registry = PluginRegistry()
registry.auto_discover()
conductor = Conductor(
    registry=registry,
    budget=5.0,
    compete=True,
    compete_agents=["planforge", "opencode"],
)

result = conductor.run_plan(plan, project_dir="./my-project")
print(f"Success: {result['success']}")
print(f"Artifacts: {len(result['artifacts'])}")
print(f"Cost: ${sum(r.cost_usd for r in result.get('candidates', []))}")
```

## Extending — Add a Domain

```python
# domains/pcb/plugin.py
from slopcontrol.core.domain_base import DomainPlugin

class PCBPlugin(DomainPlugin):
    name = "pcb"
    display_name = "PCB Design"

    def get_tools(self): ...
    def get_verifiers(self): ...
    def scaffold_project(self, path): ...
```

Place under `slopcontrol/domains/pcb/` — auto-discovered on `orchestrate`.

## Dependencies

### Core
- **deepagents**: Agent framework with planning
- **langchain**: LLM integration
- **typer**: CLI
- **qdrant-client**: Vector DB (falls back to brute-force)
- **fastapi + uvicorn**: Gateway
- **rich + textual**: Terminal UI

### Optional CAD
- **llmcad**, **build123d**, **trimesh**

### Optional Code
- **pytest**, **mypy**, **ruff**

## License

MIT License — see [LICENSE](LICENSE) for details.
