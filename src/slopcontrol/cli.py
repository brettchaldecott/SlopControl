"""SlopControl CLI — command-line interface for the agentic orchestrator.

Controls AI-generated slop through structured plans, parallel verification,
and empirical truth-seeking.  Not a CAD tool — an agentic development system.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from slopcontrol.core.orchestrator import Conductor, PluginRegistry
from slopcontrol.core.plan.generator import PlanGenerator
from slopcontrol.core.plan.renderer import read_plan, render_plan
from slopcontrol.core.providers.registry import list_available_models
from slopcontrol.core.utils.terminal import (
    display_error,
    display_info,
    display_success,
    display_warning,
)

load_dotenv()

app = typer.Typer(
    name="slopcontrol",
    help="SlopControl — Agentic development through plan-controlled verification",
    add_completion=False,
)

console = Console()

_DEFAULT_PLAN = "slop_control.md"


def _project_dir(project: Optional[str]) -> Path:
    return Path(project or os.environ.get("SLOPCONTROL_PROJECT_DIR", "."))


def _plan_path(project_dir: Path, plan_file: Optional[str]) -> Path:
    return project_dir / (plan_file or _DEFAULT_PLAN)


# ----------------------------------------------------------------------
# init
# ----------------------------------------------------------------------


@app.command()
def init(
    project_name: str = typer.Argument(..., help="Name of the project"),
    domain: str = typer.Option("code", "--domain", "-d", help="Primary domain (cad, code)"),
    multi: bool = typer.Option(False, "--multi", help="Multi-domain workspace"),
    project_dir: Optional[str] = typer.Option(None, "--dir", help="Parent directory"),
    git: bool = typer.Option(True, "--git/--no-git", help="Initialise git"),
) -> None:
    """Initialise a new SlopControl project."""
    parent = Path(project_dir) if project_dir else Path.cwd()
    project_path = parent / project_name

    if project_path.exists():
        display_error(f"Project '{project_name}' already exists at {project_path}")
        raise typer.Exit(1)

    project_path.mkdir(parents=True)

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
        f"A SlopControl project ({', '.join(domains)}).\n\n"
        f"## Usage\n"
        f"```bash\n"
        f"cd {project_path}\n"
        f"slopcontrol plan generate --request 'Build something'\n"
        f"slopcontrol orchestrate\n"
        f"```\n"
    )
    readme.write_text(readme_text)

    display_success(f"Created project '{project_name}' at {project_path}")

    if git:
        from slopcontrol.domains.cad.tools.git_ops import init_git_repo
        result = init_git_repo.invoke({"project_path": str(project_path)})
        display_success(result)


# ----------------------------------------------------------------------
# orchestrate  —  PRIMARY COMMAND
# ----------------------------------------------------------------------


@app.command()
def orchestrate(
    plan_file: Optional[str] = typer.Argument(None, help=f"Path to {_DEFAULT_PLAN} (default: ./{_DEFAULT_PLAN})"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    section: str = typer.Option("all", "--section", "-s", help="Section to execute"),
    resume: bool = typer.Option(False, "--resume", help="Resume from checkpoint"),
    budget: float = typer.Option(5.0, "--budget", help="Daily USD budget cap"),
    compete: bool = typer.Option(False, "--compete", help="Run competing agents per step"),
    compete_agents: str = typer.Option("", "--compete-agents", help="Comma-separated agent names"),
    compete_judge: str = typer.Option("hybrid", "--compete-judge", help="Judge: pass_rate|cost|speed|hybrid"),
) -> None:
    """Execute a plan via the Central Conductor.

    Reads the plan, discovers domains, dispatches steps, runs verification,
    checkpoints state.  Use --compete to run multiple agents in parallel
    for each step and pick the best via verifier pass-rate.
    """
    project_dir = _project_dir(project)
    plan_path = _plan_path(project_dir, plan_file)

    if not plan_path.exists():
        display_error(f"No plan found at {plan_path}")
        raise typer.Exit(1)

    plan_obj = read_plan(plan_path)
    console.print(
        Panel.fit(
            f"[bold cyan]SlopControl Conductor[/bold cyan]\n"
            f"Plan: {plan_obj.name}\n"
            f"Domain: {plan_obj.domain}\n"
            f"Version: {plan_obj.version}\n"
            f"Sections: {len(plan_obj.implementation_steps)}",
            border_style="cyan",
        )
    )

    if resume:
        from slopcontrol.core.orchestrator.persistence import exists, load
        if exists(project_dir):
            state = load(project_dir)
            console.print(f"[dim]Resuming from step {state.current_step}[/dim]\n")
        else:
            display_warning("No checkpoint found — starting fresh")

    registry = PluginRegistry()
    registry.auto_discover()
    agent_list = [a.strip() for a in compete_agents.split(",")] if compete_agents else None
    conductor = Conductor(
        registry=registry,
        budget=budget,
        compete=compete,
        compete_agents=agent_list,
        compete_judge=compete_judge,
    )

    display_info("Running conductor...")
    if compete:
        display_info(f"Competition mode: {compete_agents or 'auto'}, judge={compete_judge}")
    result = conductor.run_plan(plan=plan_obj, project_dir=project_dir)

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
# plan  —  plan management
# ----------------------------------------------------------------------


@app.command()
def plan(
    action: str = typer.Argument("show", help="Action: create, show, generate, update"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    name: str = typer.Option("", "--name", "-n", help="Plan name"),
    request: str = typer.Option("", "--request", "-r", help="Requirements for plan generation"),
    domain: str = typer.Option("code", "--domain", "-d", help="Primary domain"),
) -> None:
    """Manage the slop_control.md artifact."""
    project_dir = _project_dir(project)
    plan_path = _plan_path(project_dir, None)

    if action == "create":
        from slopcontrol.core.plan.schema import DesignPlan
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
        display_info("Use 'slopcontrol plan generate' to regenerate with new requirements.")

    else:
        display_error(f"Unknown action: {action}")
        raise typer.Exit(1)


# ----------------------------------------------------------------------
# verify
# ----------------------------------------------------------------------


@app.command()
def verify(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    domain: str = typer.Option("code", "--domain", "-d", help="Domain: cad, code"),
) -> None:
    """Run verification checks for the current project."""
    project_dir = _project_dir(project)

    if not (_plan_path(project_dir, None)).exists():
        display_error(f"No {_DEFAULT_PLAN} found in {project_dir}")
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
        try:
            results.extend(verifier.validate(str(project_dir)))
        except Exception as exc:
            display_warning(f"Verifier error: {exc}")

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
# mcp
# ----------------------------------------------------------------------


@app.command()
def mcp(
    action: str = typer.Argument("start", help="Action: start, stop, status"),
    port: int = typer.Option(8765, "--port", "-p", help="Port for MCP server"),
    transport: str = typer.Option("stdio", "--transport", "-t", help="Transport type"),
) -> None:
    """Manage the SlopControl MCP server."""
    if action == "start":
        try:
            from slopcontrol.integrations.mcp.server import create_mcp_server
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
        display_info("Use 'slopcontrol mcp start' to launch")
    elif action == "stop":
        display_info("Stop MCP with Ctrl+C")
    else:
        display_error(f"Unknown action: {action}")
        raise typer.Exit(1)


# ----------------------------------------------------------------------
# gateway
# ----------------------------------------------------------------------


@app.command()
def gateway(
    action: str = typer.Argument("start", help="Action: start, status"),
    port: int = typer.Option(None, "--port", "-p", help="Port"),
) -> None:
    """Manage the SlopControl LLM gateway server."""
    from slopcontrol.core.gateway import GatewayConfig, create_gateway_app

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


# ----------------------------------------------------------------------
# tui
# ----------------------------------------------------------------------


@app.command()
def tui(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model"),
    provider: str = typer.Option("auto", "--provider", help="LLM provider"),
) -> None:
    """Launch the interactive TUI."""
    from .tui import run_tui

    project_dir = project or os.environ.get("SLOPCONTROL_PROJECT_DIR", "./projects")
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


# ----------------------------------------------------------------------
# list_models / models
# ----------------------------------------------------------------------


@app.command("list-models")
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


# ----------------------------------------------------------------------
# help
# ----------------------------------------------------------------------


@app.command()
def help_cmd() -> None:
    """Show help and usage information."""
    text = (
        "# SlopControl — Agentic Development System\n\n"
        "Controls AI-generated slop through structured plans, verification loops, "
        "and empirical truth-seeking.\n\n"
        "## Quick Start\n"
        "1. Initialise:  slopcontrol init my-project --domain code\n"
        "2. Generate plan:  slopcontrol plan generate --request 'Build a REST API'\n"
        "3. Execute:  slopcontrol orchestrate\n\n"
        "## Core Commands\n"
        "- init <name>           Create project (cad / code / --multi)\n"
        "- orchestrate          Run conductor on slop_control.md\n"
        "- plan (create|show|generate|update) Manage plan\n"
        "- verify               Run domain verifiers\n\n"
        "## Infrastructure\n"
        "- gateway              Manage LLM gateway (multi-provider routing)\n"
        "- mcp                  Manage MCP server (tool exposure)\n"
        "- list-models          List available LLM models\n\n"
        "## Environment\n"
        "- SLOPCONTROL_MODEL       Default LLM model\n"
        "- SLOPCONTROL_PROJECT_DIR  Default project directory\n"
        "- SLOPCONTROL_GATEWAY_PORT Gateway listen port\n"
        "- SLOPCONTROL_LLM_CHAIN    Fallback model chain\n"
    )
    console.print(Panel.fit(text, title="SlopControl Help", border_style="cyan"))


def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "help":
        help_cmd()
        return
    app()


if __name__ == "__main__":
    main()
