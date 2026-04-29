# Installation

## Requirements

- Python 3.11 or higher
- pip or uv package manager

## Install from PyPI

```bash
pip install slopcontrol
```

## Install with uv

```bash
uv add slopcontrol
```

## Install for Development

```bash
git clone https://github.com/brettchaldecott/SlopControl.git
cd SlopControl
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Verify Installation

```bash
python -c "from slopcontrol import Conductor; print('SlopControl installed successfully!')"
```

## Environment Setup

Create a `.env` file in your project directory:

```bash
# Required for Grok models
GROK_API_KEY=xai-your-key-here

# Optional: OpenAI models
OPENAI_API_KEY=sk-your-key-here

# Optional: Ollama for local models
OLLAMA_BASE_URL=http://localhost:11434

# Optional: Default settings (Grok prioritized)
SLOPCONTROL_MODEL=grok:grok-3-beta
SLOPCONTROL_PROJECT_DIR=./projects
SLOPCONTROL_LLM_CHAIN=grok:grok-3-beta,kimi:moonshot-v1-128k,qwen:qwen-max,ollama:qwen2.5
```

## Dependencies

### Core
- **deepagents** — Agent framework with planning and filesystem tools
- **langchain-core** — LLM integration
- **typer** — CLI framework
- **rich** — Terminal output formatting
- **qdrant-client** — Vector database (falls back to brute-force in-memory)
- **fastapi + uvicorn** — LLM gateway server

### Optional
- **langchain-openai** — OpenAI model support
- **langchain-ollama** — Ollama local model support
- **pytest, mypy, ruff** — Code verification (used by the `code` domain)
- **gitpython** — Git integration
