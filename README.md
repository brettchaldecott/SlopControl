# SlopControl

**Agentic Development Through Plan-Controlled Verification**

[![PyPI version](https://img.shields.io/pypi/v/slopcontrol)](https://pypi.org/project/slopcontrol/)
[![Python](https://img.shields.io/pypi/pyversions/slopcontrol)](https://pypi.org/project/slopcontrol/)
[![License](https://img.shields.io/github/license/brettchaldecott/SlopControl)](LICENSE)

SlopControl is an **agentic development system**. It treats AI-generated code as disposable slop — controlled and refined through structured plans, empirical verification, and competing agent tournaments.

**The plan (`slop_control.md`) is the source of truth. Everything else is ephemeral.**

## Philosophy

Most AI coding assistants treat generated code as sacred. SlopControl flips this:

- **The plan is durable** — it describes requirements, decisions, and verification criteria.
- **The code is slop** — generated, tested, verified, and regenerated until it passes.
- **Agents compete** — multiple candidates per step, verifier picks the winner.
- **Costs are tracked** — every LLM call is metered with daily budget caps.
- **Truth accumulates** — historical performance per (task, agent, model) guides future selections.

## Features

- **Plan-First Workflow**: Natural language → `slop_control.md` → executed in verified steps
- **Central Conductor**: Reads plans, dispatches to agents, coordinates handoffs
- **Parallel Competition**: Multiple agent candidates per step — verifier picks winner (`--compete`)
- **Cost Tracking**: Daily budget caps with historical spend logging
- **Truth Database**: Empirical performance records per task/agent/model
- **Knowledge Base**: RAG with Qdrant + RAPTOR hierarchical summaries
- **LLM Gateway**: OpenAI-compatible proxy with automatic fallback (Grok, OpenAI, Ollama, local)
- **Local Model Discovery**: Auto-probes LM Studio, vLLM, llama.cpp on startup
- **MCP Server**: Expose tools to Claude Desktop, Cursor, OpenCode

## Installation

```bash
pip install slopcontrol
```

Or with uv:

```bash
uv add slopcontrol
```

## Quick Start

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

## CLI Commands

```bash
# Core workflow
slopcontrol init <name> [--domain code] [--multi]
slopcontrol plan generate --request "..."
slopcontrol orchestrate [--compete] [--budget 5.0] [--compete-agents planforge,opencode]
slopcontrol verify --domain code

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

## Domain: Software (`domains/code/`)

| Category | Tools |
|---|---|
| **Code** | read_code, write_code, edit_code, delete_file |
| **File ops** | list_files, create_module, move_file, find_in_files |
| **Testing** | run_tests (pytest), run_linter (ruff), run_type_check (mypy) |
| **Dependencies** | add_dependency, remove_dependency, list_dependencies |
| **Git** | init_git_repo, commit, get_history, create_branch, merge_branch |

| Verifiers | What they check |
|---|---|
| pytest | All tests pass |
| mypy | Type errors |
| coverage | Line coverage threshold |

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      User / CLI                          │
└───────────────────────┬──────────────────────────────────┘
                        │
        ┌───────────────▼──────────────┐
        │    Central Conductor         │
        │  plan → budget → compete →   │
        │   verify → truth → persist   │
        └───────┬──────────┬───────────┘
                │          │
    ┌───────────▼──────┐  ┌▼──────────────┐
    │  Code Agent      │  │  Truth DB     │
    │  ┌──┐ ┌──┐ ┌──┐ │  │  (KB records) │
    │  │RW│ │TS│ │DE│ │  └───────────────┘
    │  └──┘ └──┘ └──┘ │
    │    Competition   │        ┌──────────┐
    │    (parallel)    │        │ Verifiers│
    └──────────────────┘        │pytest    │
         │         │            │mypy      │
    ┌────▼────┐  ┌▼──────┐    │coverage  │
    │ Cost    │  │KB     │    └──────────┘
    │ Tracker │  │RAG    │
    └─────────┘  └───────┘
         │
┌────────▼────────────────────────────────────────┐
│          LLM Gateway (optional)                    │
│  OpenAI-compatible /v1/chat/completions       │
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
print(f"Cost: ${sum(r.cost_usd for r in result.get('candidates', []))}")
```

## Extending — Add a Domain

```python
# domains/web/plugin.py
from slopcontrol.core.domain_base import DomainPlugin

class WebPlugin(DomainPlugin):
    name = "web"
    display_name = "Web Development"
    def get_tools(self): ...
    def get_verifiers(self): ...
    def scaffold_project(self, path): ...
```

Place under `slopcontrol/domains/web/` — auto-discovered on `orchestrate`.

## Dependencies

### Core
- **deepagents**: Agent framework with planning
- **langchain**: LLM integration
- **typer**: CLI
- **qdrant-client**: Vector DB (falls back to brute-force)
- **fastapi + uvicorn**: LLM gateway
- **rich + textual**: Terminal UI

### Optional
- **pytest**, **mypy**, **ruff**: Code verification

## License

MIT License — see [LICENSE](LICENSE) for details.
