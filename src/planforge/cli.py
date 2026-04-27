"""PlanForge CLI — command-line interface for the multi-domain orchestrator."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from planforge.core.orchestrator import Conductor, PluginRegistry
from planforge.core.plan.generator import PlanGenerator
from planforge.core.plan.renderer import read_plan, render_plan
from planforge.core.providers.registry import list_available_models
from planforge.core.utils.terminal import (
    display_error,
    display_info,
    display_success,
    display_warning,
)

from .agent import create_cad_agent, run_design_session

load_dotenv()

app = typer.Typer(
    name="planforge",
    help="PlanForge — AI-powered plan orchestration for CAD & software",
    add_completion=False,
)

console = Console()

# ----------------------------------------------------------------------
# init
# ----------------------------------------------------------------------


@app.command()
def init(
    project_name: str = typer.Argument(..., help="Name of the project"),
    domain: str = typer.Option("cad", "--domain", "-d", help="Primary domain (cad, code)"),
    multi: bool = typer.Option(False, "--multi", help="Multi-domain workspace"),
    project_dir: Optional[str] = typer.Option(None, "--dir", help="Parent directory"),
    git: bool = typer.Option(True, "--git/--no-git", help="Initialise git"),
) -> None:
    """Initialise a new PlanForge project."""
    parent = Path(project_dir) if project_dir else Path.cwd()
    project_path = parent / project_name

    if project_path.exists():
        display_error(f"Project '{project_name}' already exists at {project_path}")
        raise typer.Exit(1)

    project_path.mkdir(parents=True)

    # Scaffold from domain plugin(s)
    registry = PluginRegistry()
    registry.auto_discover()

    domains = ["cad", "code"] if multi else [domain]
    for d in domains:
        if registry.has(d):
            registry.get(d).scaffold_project(project_path)
        else:
            display_warning(f"Unknown domain '{d}' — skipping scaffold")

    readme = project_path / "README.md"
    readme_text = (
        f"# {project_name}\n\n"
        f"A PlanForge project ({', '.join(domains)}).\n\n"
        f"## Usage\n"
        f"```bash\n"
        f"cd {project_path}\n"
        f"planforge orchestrate\n"
        f"```\n"
    )
    readme.write_text(readme_text)

    display_success(f"Created project '{project_name}' at {project_path}")

    if git:
        from planforge.domains.cad.tools.git_ops import init_git_repo

        result = init_git_repo.invoke({"project_path": str(project_path)})
        display_success(result)


# ----------------------------------------------------------------------
# orchestrate  —  NEW primary command
# ----------------------------------------------------------------------


@app.command()
def orchestrate(
    plan_file: Optional[str] = typer.Argument(None, help="Path to plan_forge.md (default: ./plan_forge.md)"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    section: str = typer.Option("all", "--section", "-s", help="Section to execute"),
    resume: bool = typer.Option(False, "--resume", help="Resume from checkpoint"),
) -> None:
    """Execute a plan via the Central Conductor.

    Reads the plan, discovers domains, dispatches steps, and runs
    verification.  Checkpoints state so interrupted runs can resume.
    """
    project_dir = Path(project or os.environ.get("PLANFORGE_PROJECT_DIR", "."))
    plan_path = project_dir / (plan_file or "plan_forge.md")

    if not plan_path.exists():
        display_error(f"No plan found at {plan_path}")
        raise typer.Exit(1)

    plan_obj = read_plan(plan_path)
    console.print(
        Panel.fit(
            f"[bold cyan]PlanForge Conductor[/bold cyan]\n"
            f"Plan: {plan_obj.name}\n"
            f"Domain: {plan_obj.domain}\n"
            f"Version: {plan_obj.version}\n"
            f"Sections: {len(plan_obj.implementation_steps)}",
            border_style="cyan",
        )
    )

    if resume:
        from planforge.core.orchestrator.persistence import exists, load

        if exists(project_dir):
            state = load(project_dir)
            console.print(f"[dim]Resuming from step {state.current_step}[/dim]\n")
        else:
            display_warning("No checkpoint found — starting fresh")

    registry = PluginRegistry()
    registry.auto_discover()
    conductor = Conductor(registry=registry)

    display_info("Running conductor...")
    result = conductor.run_plan(plan=plan_obj, project_dir=project_dir)

    # Display results
    all_ok = result["success"]
    if all_ok:
        display_success("Orchestration complete — all steps passed")
    else:
        display_warning("Some steps failed — review the log above")

    console.print(f"\n[bold]Artifacts:[/bold] {len(result['artifacts'])}")
    console.print(f"[bold]Handoffs:[/bold] {len(result['handoffs'])}")
    if result["errors"]:
        console.print(f"[bold red]Errors:[/bold red] {len(result['errors'])}")
        for e in result["errors"]:
            console.print(f"  Step {e['step']}: {e['message']}")

    if not all_ok:
        raise typer.Exit(1)


# ----------------------------------------------------------------------
# design  —  kept for backward compat
# ----------------------------------------------------------------------


@app.command()
def design(
    prompt: Optional[str] = typer.Argument(None, help="Design request"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model"),
    provider: str = typer.Option("auto", "--provider", help="LLM provider"),
    interactive: bool = typer.Option(True, "--interactive/--headless", help="Interactive mode"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Stream responses"),
    auto_preview: bool = typer.Option(True, "--auto-preview/--no-preview", help="Auto-display previews"),
) -> None:
    """Run a legacy CAD design session.

    Deprecated: use ``planforge orchestrate`` for multi-domain plans.
    """
    display_warning("'design' is a legacy command. Consider using 'orchestrate' instead.")

    console.print(
        Panel.fit(
            "[bold cyan]PlanForge[/bold cyan] — CAD Design",
            border_style="cyan",
        )
    )

    project_dir = project or os.environ.get("PLANFORGE_PROJECT_DIR", "./projects")

    if not Path(project_dir).exists():
        display_warning(f"Project directory '{project_dir}' does not exist.")
        create_new = typer.confirm("Create it?", default=True)
        if create_new:
            Path(project_dir).mkdir(parents=True, exist_ok=True)
        else:
            raise typer.Exit(1)

    if prompt is None:
        console.print("\n[bold]Enter your design request:[/bold]")
        prompt = typer.prompt("", default="Create a simple 50mm cube")

    try:
        result = run_design_session(
            prompt=prompt,
            model=model,
            provider=provider,
            project_dir=project_dir,
            interactive=interactive,
        )
        console.print("\n[bold green]Design session completed![/bold green]")
        if stream and interactive:
            for chunk in result.get("stream", []):
                if hasattr(chunk, "content"):
                    console.print(chunk.content, end="")
    except Exception as e:
        display_error(f"Error: {e}")
        raise typer.Exit(1)


# ----------------------------------------------------------------------
# plan  —  enhanced
# ----------------------------------------------------------------------


@app.command()
def plan(
    action: str = typer.Argument("show", help="Action: create, show, generate, update"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    name: str = typer.Option("", "--name", "-n", help="Plan name"),
    request: str = typer.Option("", "--request", "-r", help="Requirements for plan generation"),
    domain: str = typer.Option("cad", "--domain", "-d", help="Primary domain"),
) -> None:
    """Manage the plan_forge.md artifact."""
    project_dir = Path(project or os.environ.get("PLANFORGE_PROJECT_DIR", "."))
    plan_path = project_dir / "plan_forge.md"

    if action == "create":
        from planforge.core.plan.schema import DesignPlan

        plan_obj = DesignPlan(
            name=name or project_dir.name,
            domain=domain,
            requirements=[request] if request else [],
            tags=[domain],
        )
        render_plan(plan_obj, plan_path)
        display_success(f"Created {plan_path}")

    elif action == "generate":
        if not request:
            request = typer.prompt("Requirements for the plan")

        generator = PlanGenerator()
        plan_obj = generator.generate(request=request, domain=domain, name=name or project_dir.name)
        render_plan(plan_obj, plan_path)
        display_success(f"Generated plan at {plan_path}")

    elif action == "show":
        if not plan_path.exists():
            display_error(f"No plan found at {plan_path}")
            raise typer.Exit(1)

        plan_obj = read_plan(plan_path)
        console.print(f"\n[bold cyan]Plan: {plan_obj.name}[/bold cyan]")
        console.print(f"Domain: {plan_obj.domain}")
        console.print(f"Version: {plan_obj.version}")
        console.print(f"Status: {plan_obj.status}")
        console.print(f"\n[bold]Requirements:[/bold]")
        for req in plan_obj.requirements:
            console.print(f"  - {req}")

    elif action == "update":
        display_info("Use 'planforge plan generate' to regenerate with new requirements.")

    else:
        display_error(f"Unknown action: {action}")
        raise typer.Exit(1)


# ----------------------------------------------------------------------
# execute  —  enhanced with domain dispatch
# ----------------------------------------------------------------------


@app.command()
def execute(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    agent: str = typer.Option("planforge", "--agent", "-a", help="Agent: planforge, opencode, claude, cursor"),
    section: str = typer.Option("all", "--section", "-s", help="Plan section to execute"),
    domain: str = typer.Option("", "--domain", "-d", help="Override domain (auto-detect if empty)"),
) -> None:
    """Execute the current plan using the specified agent."""
    project_dir = Path(project or os.environ.get("PLANFORGE_PROJECT_DIR", "."))
    plan_path = project_dir / "plan_forge.md"

    if not plan_path.exists():
        display_error(f"No plan found at {plan_path}")
        raise typer.Exit(1)

    display_info(f"Executing plan section '{section}' with agent '{agent}'")

    plan_obj = read_plan(plan_path)
    effective_domain = domain or plan_obj.domain

    if agent == "planforge":
        registry = PluginRegistry()
        registry.auto_discover()
        conductor = Conductor(registry=registry)
        result = conductor.run_plan(plan=plan_obj, project_dir=project_dir)
        if result["success"]:
            display_success("PlanForge execution complete")
        else:
            display_error("Some steps failed")
            raise typer.Exit(1)

    elif agent in ("opencode", "claude", "cursor"):
        from planforge.integrations.opencode import OpenCodeAdapter
        from planforge.integrations.claude import ClaudeAdapter
        from planforge.integrations.cursor import CursorAdapter

        task = "\n".join(plan_obj.requirements)
        adapter = {
            "opencode": OpenCodeAdapter(),
            "claude": ClaudeAdapter(),
            "cursor": CursorAdapter(),
        }[agent]
        result = adapter.execute(task=task, context_dir=project_dir)
        console.print(result.get("stdout", ""))
        if not result.get("success"):
            display_error(result.get("stderr", "External agent failed"))
            raise typer.Exit(1)

    else:
        display_error(f"Unknown agent: {agent}")
        raise typer.Exit(1)


# ----------------------------------------------------------------------
# verify
# ----------------------------------------------------------------------


@app.command()
def verify(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    domain: str = typer.Option("cad", "--domain", "-d", help="Domain: cad, code"),
    max_overhang: float = typer.Option(45.0, "--max-overhang", help="Max overhang angle (CAD only)"),
    min_wall: float = typer.Option(0.8, "--min-wall", help="Min wall thickness mm (CAD only)"),
    coverage_threshold: float = typer.Option(80.0, "--coverage-threshold", help="Min coverage % (code only)"),
) -> None:
    """Run verification checks for the current project."""
    project_dir = Path(project or os.environ.get("PLANFORGE_PROJECT_DIR", "."))

    if not (project_dir / "plan_forge.md").exists():
        display_error(f"No plan_forge.md found in {project_dir}")
        raise typer.Exit(1)

    display_info(f"Running L3 verification for {domain} domain")

    registry = PluginRegistry()
    registry.auto_discover()

    if not registry.has(domain):
        display_error(f"No plugin registered for domain '{domain}'")
        raise typer.Exit(1)

    verifiers = registry.get(domain).get_verifiers()
    results: list[Any] = []
    for verifier in verifiers:
        results.extend(verifier.validate(str(project_dir)))

    console.print(f"\n[bold]Verification Results ({domain}):[/bold]\n")
    all_pass = True
    for r in results:
        icon = "[green]✓[/green]" if r.passed else "[red]✗[/red]"
        console.print(f"{icon} {r.check}: {r.message}")
        if not r.passed:
            all_pass = False

    if all_pass:
        display_success("All checks passed!")
    else:
        display_warning("Some checks failed.")
        raise typer.Exit(1)


# ----------------------------------------------------------------------
# Remaining commands (unchanged)
# ----------------------------------------------------------------------


@app.command()
def mcp(
    action: str = typer.Argument("start", help="Action: start, stop, status"),
    port: int = typer.Option(8765, "--port", "-p", help="Port for MCP server"),
    transport: str = typer.Option("stdio", "--transport", "-t", help="Transport type"),
) -> None:
    """Manage the PlanForge MCP server."""
    if action == "start":
        try:
            from planforge.integrations.mcp.server import create_mcp_server
            import asyncio

            display_info(f"Starting MCP server on port {port}...")
            server = create_mcp_server()
            asyncio.run(server.run(transport=transport))
        except ImportError:
            display_error("MCP not installed: pip install mcp")
            raise typer.Exit(1)
        except Exception as e:
            display_error(f"MCP failed: {e}")
            raise typer.Exit(1)
    elif action == "status":
        display_info("Use 'planforge mcp start' to launch")
    elif action == "stop":
        display_info("Stop MCP with Ctrl+C")
    else:
        display_error(f"Unknown action: {action}")
        raise typer.Exit(1)


@app.command()
def gateway(
    action: str = typer.Argument("start", help="Action: start, status"),
    port: int = typer.Option(None, "--port", "-p", help="Port"),
) -> None:
    """Manage the PlanForge LLM gateway server."""
    from planforge.core.gateway import GatewayConfig, create_gateway_app

    cfg = GatewayConfig.from_env()
    if port is not None:
        cfg.gateway_port = port

    if action == "start":
        try:
            import uvicorn
            display_info(f"Starting gateway on {cfg.gateway_url}")
            fast_app = create_gateway_app()
            uvicorn.run(fast_app, host=cfg.gateway_host, port=cfg.gateway_port, log_level="info")
        except ImportError:
            display_error("Gateway requires fastapi+uvicorn")
            raise typer.Exit(1)
        except Exception as e:
            display_error(f"Gateway failed: {e}")
            raise typer.Exit(1)
    elif action == "status":
        display_info(f"Gateway at {cfg.gateway_url}")
    else:
        display_error(f"Unknown action: {action}")
        raise typer.Exit(1)


@app.command()
def tui(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model"),
    provider: str = typer.Option("auto", "--provider", help="LLM provider"),
) -> None:
    """Launch the interactive TUI."""
    from .tui import run_tui

    project_dir = project or os.environ.get("PLANFORGE_PROJECT_DIR", "./projects")
    project_path = Path(project_dir)
    if not project_path.exists():
        display_warning(f"Project '{project_dir}' does not exist.")
        if typer.confirm("Create it?", default=True):
            project_path.mkdir(parents=True, exist_ok=True)
        else:
            raise typer.Exit(1)

    try:
        run_tui(project_path=project_path, model=model, provider=provider)
    except ImportError as e:
        display_error(f"TUI requires textual: {e}")
        raise typer.Exit(1)
    except Exception as e:
        display_error(f"TUI error: {e}")
        raise typer.Exit(1)


@app.command()
def export(
    design_name: str = typer.Argument(..., help="Name of the design to export"),
    format: str = typer.Option("stl", "--format", "-f", help="Export format"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
) -> None:
    """Export a design to a CAD file format."""
    from planforge.domains.cad.tools.file_ops import load_design_state
    from planforge.domains.cad.tools.cad import export_model

    project_dir = project or os.environ.get("PLANFORGE_PROJECT_DIR", "./projects")
    body_data = load_design_state(name=design_name, project_path=project_dir)
    if body_data.startswith("Error"):
        display_error(body_data)
        raise typer.Exit(1)

    if output is None:
        out_dir = Path(project_dir) / "exports"
        out_dir.mkdir(exist_ok=True)
        output = str(out_dir / f"{design_name}.{format.lower()}")

    result = export_model.invoke({"body_data": body_data, "format": format, "path": output})
    display_success(f"Exported to {output}")


@app.command()
def list_models(
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider"),
) -> None:
    """List available LLM models."""
    models = list_available_models(provider)
    console.print("\n[bold]Available Models:[/bold]\n")
    for prov, model_list in models.items():
        console.print(f"[cyan]{prov}:[/cyan]")
        for m in model_list:
            console.print(f"  - {m}")
        console.print()


@app.command()
def models(
    provider: Optional[str] = typer.Argument(None, help="Provider to list models for"),
) -> None:
    """Alias for list-models."""
    list_models(provider)


@app.command()
def history(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    max_count: int = typer.Option(10, "--count", "-n", help="Number of commits"),
) -> None:
    """Show design version history."""
    from planforge.domains.cad.tools.git_ops import get_design_history

    project_dir = project or os.environ.get("PLANFORGE_PROJECT_DIR", "./projects")
    result = get_design_history(project_path=project_dir, max_count=max_count)
    console.print(result)


@app.command()
def tools() -> None:
    """List all available CAD tools."""
    from planforge.integrations.mcp.tools import CAD_MCP_TOOLS

    console.print("\n[bold cyan]Available PlanForge Tools:[/bold cyan]\n")
    for tool in CAD_MCP_TOOLS:
        desc = tool.description.split("\n")[0][:60] if tool.description else ""
        console.print(f"  [green]{tool.name}[/green] - {desc}")


@app.command()
def help_cmd() -> None:
    """Show help and usage information."""
    text = (
        "# PlanForge - AI-Powered Plan Orchestration\n\n"
        "## Quick Start\n"
        "1. Initialise:  planforge init my-project --domain code\n"
        "2. Generate plan:  planforge plan generate --request 'Build a REST API'\n"
        "3. Execute:  planforge orchestrate\n\n"
        "## Commands\n"
        "- init <name>           Create project (cad / code / --multi)\n"
        "- orchestrate          Run conductor on plan_forge.md\n"
        "- plan (create|show|generate|update) Manage plan\n"
        "- execute              Execute plan (legacy)\n"
        "- design               Legacy CAD session\n"
        "- verify               Run domain verifiers\n"
        "- tools                List tools\n"
        "- models               List LLM models\n"
        "- mcp                  Manage MCP server\n"
        "- gateway              Manage LLM gateway\n\n"
        "## Environment\n"
        "- PLANFORGE_MODEL       Default LLM model\n"
        "- PLANFORGE_PROJECT_DIR Default project directory\n"
    )
    console.print(Panel.fit(text, title="PlanForge Help", border_style="cyan"))


def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "help":
        help_cmd()
        return
    app()


if __name__ == "__main__":
    main()
