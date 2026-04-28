# Quick Start Guide

## 1. Initialize a Project

```bash
slopcontrol init my-api --domain code
cd my-api
```

This creates a new project with the following structure:
```
my-api/
├── slop_control.md   # The plan artifact
├── src/              # Source code
└── tests/            # Test suite
```

## 2. Generate a Plan

Describe what you want to build:

```bash
slopcontrol plan generate --request "Build a FastAPI REST API with CRUD, SQLite, Pydantic, and pytest"
```

The agent will:
1. Understand your request
2. Write a structured plan to `slop_control.md`
3. Include requirements, design decisions, and implementation steps

## 3. Execute the Plan

Run the Central Conductor to execute each step:

```bash
slopcontrol orchestrate
```

The conductor:
1. Reads the plan
2. Dispatches each step to the appropriate domain agent
3. Runs verifiers after each step
4. Checkpoints state so you can resume

### With Competition Mode

Run multiple agents in parallel per step and let the verifier pick the winner:

```bash
slopcontrol orchestrate --compete --compete-agents grok,openai --budget 5.00
```

## 4. Iterate on Your Design

When you want to make changes, just update the plan and re-run:

```bash
# Edit slop_control.md, then:
slopcontrol orchestrate --resume
```

Or regenerate from a new request:

```bash
slopcontrol plan generate --request "Add OAuth2 authentication to the API"
```

## 5. Verify

Run domain verifiers to ensure everything passes:

```bash
slopcontrol verify --domain code
```

## Common Patterns

### REST API
```
Build a REST API with FastAPI, SQLite, and JWT authentication
```

### CLI Tool
```
Build a CLI tool with Typer that manages task lists
```

### Library
```
Build a Python library with a clean public API, comprehensive tests, and type hints
```

## Next Steps

- [MCP Setup](mcp_setup.md) — Use SlopControl tools from AI coding assistants like Cursor
- [Installation](installation.md) — Detailed installation and configuration
