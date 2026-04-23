# Installation

## Requirements

- Python 3.11 or higher
- pip or uv package manager

## Install from PyPI

```bash
pip install cadAI
```

## Install with uv

```bash
uv add cadAI
```

## Install for Development

```bash
git clone https://github.com/yourusername/PlanForge.git
cd PlanForge
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Verify Installation

```bash
python -c "from planforge import create_cad_agent; print('PlanForge installed successfully!')"
```

## Environment Setup

Create a `.env` file in your project directory:

```bash
# Required for OpenAI models
OPENAI_API_KEY=your_openai_api_key_here

# Required for Anthropic models
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Ollama for local models
OLLAMA_BASE_URL=http://localhost:11434

# Optional: Default settings
PLANFORGE_MODEL=openai:gpt-4o
PLANFORGE_PROJECT_DIR=./projects
```

## Dependencies

PlanForge requires the following packages:

- **deepagents** - Agent framework with planning and filesystem tools
- **llmcad** - LLM-friendly CAD library built on OpenCASCADE
- **langchain-core** - LLM integration
- **langchain-openai** - OpenAI model support
- **langchain-anthropic** - Anthropic model support
- **langchain-ollama** - Ollama model support
- **typer** - CLI framework
- **pillow** - Image processing for previews
- **gitpython** - Git integration for version control
- **rich** - Terminal output formatting
