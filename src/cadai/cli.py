"""CadAI CLI - Command-line interface for the CAD agent."""

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .agent import create_cad_agent, run_design_session
from .providers.registry import list_available_models
from .utils.terminal import (
    display_success,
    display_error,
    display_info,
    display_warning,
)

app = typer.Typer(
    name="cadai",
    help="CadAI - AI-powered CAD agent for natural language 3D modeling",
    add_completion=False,
)

console = Console()


@app.command()
def init(
    project_name: str = typer.Argument(..., help="Name of the project to create"),
    project_dir: Optional[str] = typer.Option(
        None, "--dir", "-d", help="Parent directory for the project"
    ),
    git: bool = typer.Option(True, "--git/--no-git", help="Initialize git repository"),
) -> None:
    """Initialize a new CadAI project."""
    from .tools.git_ops import init_git_repo

    parent = Path(project_dir) if project_dir else Path.cwd()
    project_path = parent / project_name

    if project_path.exists():
        display_error(f"Project '{project_name}' already exists at {project_path}")
        raise typer.Exit(1)

    project_path.mkdir(parents=True)
    (project_path / "designs").mkdir()
    (project_path / "exports").mkdir()
    (project_path / "previews").mkdir()

    readme = project_path / "README.md"
    readme.write_text(f"""# {project_name}

A CadAI project for designing 3D parts.

## Structure
- `designs/` - Saved design states
- `exports/` - Exported CAD files (STEP, STL, GLB)
- `previews/` - Rendered preview images

## Usage
```bash
cd {project_path}
cadai design
```
""")

    display_success(f"Created project '{project_name}' at {project_path}")

    if git:
        result = init_git_repo(str(project_path))
        display_success(result)


@app.command()
def design(
    prompt: Optional[str] = typer.Argument(None, help="Design request (omit for interactive mode)"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model to use"),
    provider: str = typer.Option(
        "auto", "--provider", help="LLM provider (openai, anthropic, ollama)"
    ),
    interactive: bool = typer.Option(True, "--interactive/--headless", help="Interactive mode"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Stream responses"),
) -> None:
    """Run a design session with the CAD agent."""
    console.print(
        Panel.fit(
            "[bold cyan]CadAI[/bold cyan] - AI-Powered CAD Designer",
            border_style="cyan",
        )
    )

    project_dir = project or os.environ.get("CADAI_PROJECT_DIR", "./projects")

    if not Path(project_dir).exists():
        display_warning(f"Project directory '{project_dir}' does not exist.")
        create_new = typer.confirm("Create it?", default=True)
        if create_new:
            Path(project_dir).mkdir(parents=True, exist_ok=True)
            display_success(f"Created {project_dir}")
        else:
            raise typer.Exit(1)

    if prompt is None:
        console.print("\n[bold]Enter your design request:[/bold]")
        prompt = typer.prompt("", default="Create a simple 50mm cube")

    console.print(f"\n[dim]Model: {model or 'auto'}[/dim]")
    console.print(f"[dim]Project: {project_dir}[/dim]\n")

    try:
        result = run_design_session(
            prompt=prompt,
            model=model,
            provider=provider,
            project_dir=project_dir,
            interactive=interactive,
        )

        if stream and interactive:
            console.print("\n[bold cyan]Agent Response:[/bold cyan]")
            agent = result["agent"]
            for chunk in result["stream"]:
                if hasattr(chunk, "content"):
                    console.print(chunk.content, end="")
                elif isinstance(chunk, dict):
                    for key, value in chunk.items():
                        if key == "messages" and value:
                            last_msg = value[-1]
                            if hasattr(last_msg, "content"):
                                console.print(last_msg.content)
        else:
            console.print("\n[bold green]Design session completed![/bold green]")

    except Exception as e:
        display_error(f"Error: {str(e)}")
        if os.environ.get("CADAI_DEBUG"):
            raise
        raise typer.Exit(1)


@app.command()
def export(
    design_name: str = typer.Argument(..., help="Name of the design to export"),
    format: str = typer.Option("stl", "--format", "-f", help="Export format (step, stl, glb)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
) -> None:
    """Export a design to a CAD file format."""
    from .tools.file_ops import load_design_state

    project_dir = project or os.environ.get("CADAI_PROJECT_DIR", "./projects")

    try:
        body_data = load_design_state(
            name=design_name,
            project_path=project_dir,
        )

        if body_data.startswith("Error"):
            display_error(body_data)
            raise typer.Exit(1)

        if output is None:
            exports_dir = Path(project_dir) / "exports"
            exports_dir.mkdir(exist_ok=True)
            output = str(exports_dir / f"{design_name}.{format.lower()}")

        from .tools.cad import export_model

        result = export_model.invoke(
            {
                "body_data": body_data,
                "format": format,
                "path": output,
            }
        )

        display_success(f"Exported to {output}")

    except Exception as e:
        display_error(f"Export failed: {str(e)}")
        raise typer.Exit(1)


@app.command()
def list_models(
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider"),
) -> None:
    """List available LLM models."""
    models = list_available_models(provider)

    console.print("\n[bold]Available Models:[/bold]\n")

    for prov, model_list in models.items():
        console.print(f"[cyan]{prov}:[/cyan]")
        for model in model_list:
            console.print(f"  - {model}")
        console.print()


@app.command()
def models(
    provider: Optional[str] = typer.Argument(None, help="Provider to list models for"),
) -> None:
    """Alias for list-models command."""
    list_models(provider)


@app.command()
def history(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    max_count: int = typer.Option(10, "--count", "-n", help="Number of commits to show"),
) -> None:
    """Show design version history."""
    from .tools.git_ops import get_design_history

    project_dir = project or os.environ.get("CADAI_PROJECT_DIR", "./projects")

    result = get_design_history(
        project_path=project_dir,
        max_count=max_count,
    )

    console.print(result)


@app.command()
def help_cmd() -> None:
    """Show help and usage information."""
    console.print(
        Panel.fit(
            """# CadAI - AI-Powered CAD Agent

## Quick Start
1. Initialize a project: `cadai init my-project`
2. Run a design session: `cadai design "Create a mounting bracket"`
3. Export your design: `cadai export bracket --format stl`

## Commands
- `init <name>` - Create a new project
- `design [prompt]` - Run a design session
- `export <name>` - Export a design
- `history` - View version history
- `models` - List available LLM models

## Environment Variables
- `CADAI_MODEL` - Default LLM model
- `CADAI_PROJECT_DIR` - Default project directory
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `OLLAMA_BASE_URL` - Ollama server URL

For more help, see the documentation at https://cadai.readthedocs.io
""",
            title="CadAI Help",
            border_style="cyan",
        )
    )


def main() -> None:
    """Main entry point for the CLI."""
    if len(sys.argv) > 1 and sys.argv[1] == "help":
        help_cmd()
        return

    app()


if __name__ == "__main__":
    main()
