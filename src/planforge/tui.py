"""Interactive TUI for PlanForge design sessions."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import (
        Header,
        Footer,
        Static,
        Input,
        Log,
        Button,
        ProgressBar,
        Tree,
    )
    from textual.widgets.tree import TreeNode
    from textual.binding import Binding
    from textual import on

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .tools.session_manager import SessionManager, DesignState
from .tools.cad import CAD_TOOLS, create_box, export_model
from .tools.visualization import render_preview
from .tools.design_history import DesignHistory
from .providers.registry import get_model


console = Console()


class DesignLog(Log):
    """Custom log widget for displaying design output."""

    def write_log(self, message: str, style: str = "") -> None:
        """Write a message to the log.

        Args:
            message: Message to display
            style: Rich style string
        """
        if style:
            self.write(message, style=style)
        else:
            self.write(message)


class PlanForgeApp(App if TEXTUAL_AVAILABLE else object):
    """Interactive PlanForge TUI application."""

    CSS = """
    Screen {
        background: $surface;
    }

    #sidebar {
        width: 28;
        border: solid $border;
        padding: 1;
    }

    #main-panel {
        border: solid $border;
    }

    #preview-area {
        border: solid $accent;
        background: $surface-darken-1;
        padding: 1;
    }

    #status-bar {
        background: $surface-darken-2;
        padding: 1;
    }

    Button {
        margin: 1 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("c", "clear_log", "Clear", show=True),
        Binding("s", "save_session", "Save", show=True),
        Binding("e", "export", "Export", show=True),
        Binding("p", "toggle_preview", "Preview", show=True),
        Binding("r", "render_preview", "Render", show=True),
    ]

    def __init__(
        self,
        project_path: Path,
        model: Optional[str] = None,
        provider: str = "auto",
    ):
        """Initialize the TUI app.

        Args:
            project_path: Path to project directory
            model: LLM model to use
            provider: LLM provider
        """
        if not TEXTUAL_AVAILABLE:
            raise ImportError("Textual is required for TUI. Install with: pip install textual")

        super().__init__()
        self.project_path = project_path
        self.model = model or "opencode:big-pickle"
        self.provider = provider
        self.session_manager = SessionManager(project_path)
        self.design_history = DesignHistory(project_path)
        self.current_design: Optional[DesignState] = None
        self.agent = None
        self.show_preview = True

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()

        with Container(id="main-container"):
            with Horizontal(id="header-area"):
                yield Static(
                    "[bold cyan]PlanForge[/bold cyan] Interactive Design Session",
                    classes="title",
                )

            with Horizontal(id="content-area"):
                with Vertical(id="sidebar"):
                    yield Static("[bold]Session[/bold]")
                    yield Button("New Session", id="btn-new", variant="primary")
                    yield Button("Load Session", id="btn-load")
                    yield Button("Save", id="btn-save")

                    yield Static("")

                    yield Static("[bold]Design[/bold]")
                    yield Button("Render Preview", id="btn-render")
                    yield Button("Toggle Preview", id="btn-toggle-preview")
                    yield Button("Export STL", id="btn-export-stl")
                    yield Button("Export STEP", id="btn-export-step")

                    yield Static("")

                    yield Static("[bold]History[/bold]")
                    yield Button("View History", id="btn-history")
                    yield Button("Compare Versions", id="btn-compare")

                    yield Static("")

                    yield Static("[bold]Iteration[/bold]")
                    yield Static("", id="iteration-display")

                with Vertical(id="main-panel"):
                    yield DesignLog(id="log-area", auto_scroll=True)
                    yield Input(
                        placeholder="Enter design command or question...",
                        id="command-input",
                    )

            with Horizontal(id="preview-area"):
                yield Static("[bold]Preview[/bold]", id="preview-title")
                yield Static("", id="preview-content")

            with Horizontal(id="status-bar"):
                yield Static("", id="status-text")

    def on_mount(self) -> None:
        """Handle app mount."""
        self.title = "PlanForge - Interactive Design Session"
        self.sub_title = f"Project: {self.project_path.name}"
        self._log("[cyan]Welcome to PlanForge![/cyan]")
        self._log("[dim]Type your design request and press Enter[/dim]")
        self._log("[dim]Commands: help, clear, quit[/dim]")
        self._log("")

        self._update_status(f"Model: {self.model}")

        input_widget = self.query_one("#command-input", Input)
        input_widget.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        command = event.value.strip()
        if command:
            asyncio.create_task(self._process_command(command))
            event.input.value = ""

    def _log(self, message: str) -> None:
        """Log a message to the log area.

        Args:
            message: Message to log
        """
        log_widget = self.query_one("#log-area", DesignLog)
        log_widget.write_log(message)

    def _update_status(self, message: str) -> None:
        """Update status bar.

        Args:
            message: Status message
        """
        status = self.query_one("#status-text", Static)
        status.update(message)

    async def _process_command(self, command: str) -> None:
        """Process a design command.

        Args:
            command: User command
        """
        self._log(f"[yellow]You:[/yellow] {command}")

        if not command.strip():
            return

        if command.lower() in ["quit", "exit", "q"]:
            self._log("[cyan]Goodbye![/cyan]")
            self.exit()
            return

        if command.lower() == "help":
            self._show_help()
            return

        if command.lower() == "clear":
            self.query_one("#log-area", DesignLog).clear()
            return

        try:
            self._log("[dim]Processing...[/dim]")

            response = await self._call_agent(command)
            self._log(f"[green]PlanForge:[/green] {response}")

            if self.current_design and self.current_design.body_data:
                self._update_preview()

        except Exception as e:
            self._log(f"[red]Error:[/red] {str(e)}")

    async def _call_agent(self, prompt: str) -> str:
        """Call the agent with a prompt.

        Args:
            prompt: User prompt

        Returns:
            Agent response
        """
        from langchain_core.messages import HumanMessage

        if self.agent is None:
            self.agent = self._create_agent()

        result = await self.agent.ainvoke({"messages": [HumanMessage(content=prompt)]})

        messages = result.get("messages", [])
        if messages:
            last = messages[-1]
            if hasattr(last, "content"):
                return last.content

        return "Design updated."

    def _create_agent(self):
        """Create the agent instance."""
        from deepagents import create_deep_agent

        chat_model = get_model(self.model, provider=self.provider)

        return create_deep_agent(
            model=chat_model,
            tools=list(CAD_TOOLS),
            system_prompt="""You are PlanForge, an expert 3D CAD designer.
Use the CAD tools to create and modify designs.
Always use millimeters (mm) as units.
After creating/modifying a body, summarize what was done.""",
        )

    def _show_help(self) -> None:
        """Show help information."""
        help_text = """
[bold cyan]PlanForge Commands:[/bold cyan]

[bold]Design:[/bold]
  create box 50x50x50    - Create a box
  create cylinder r=25  - Create a cylinder
  add fillet r=2         - Add fillet
  export stl             - Export as STL
  export step            - Export as STEP

[bold]Navigation:[/bold]
  help                  - Show this help
  clear                 - Clear log
  quit                  - Exit

[bold]Shortcuts:[/bold]
  Ctrl+C                - Quit
  c                     - Clear log
  s                     - Save session
  e                     - Export
  p                     - Toggle preview
  r                     - Render preview
"""
        self._log(help_text)

    def _update_preview(self) -> None:
        """Update the preview display."""
        if not self.current_design or not self.current_design.body_data:
            return

        preview = self.query_one("#preview-content", Static)

        info = self.current_design.model_info
        dims = info.get("dimensions", {})

        preview_text = f"""
[bold]Model Info:[/bold]
  Name: {self.current_design.body_name or "unnamed"}
  Iteration: {self.current_design.iteration}
  
[bold]Dimensions:[/bold]
  Width:  {dims.get("width", "N/A"):.2f} mm
  Height: {dims.get("height", "N/A"):.2f} mm
  Depth:  {dims.get("depth", "N/A"):.2f} mm
  
[bold]Properties:[/bold]
  Volume: {info.get("volume", "N/A"):.2f} mm³
  Faces:  {info.get("face_count", "N/A")}
"""
        preview.update(preview_text)

        iter_display = self.query_one("#iteration-display", Static)
        iter_display.update(f"Iteration: {self.current_design.iteration}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "btn-new":
            self._log("[cyan]Starting new session...[/cyan]")
            self.current_design = self.session_manager.create_session(
                f"design_{self.session_manager.sessions_dir.parent.name}"
            )
            self._log(f"[green]Session created:[/green] {self.current_design.name}")

        elif button_id == "btn-load":
            sessions = self.session_manager.list_sessions()
            if sessions:
                self._log(f"[cyan]Available sessions:[/cyan] {', '.join(sessions)}")
            else:
                self._log("[yellow]No saved sessions[/yellow]")

        elif button_id == "btn-save":
            if self.current_design:
                self.session_manager.save_session()
                self._log("[green]Session saved![/green]")
            else:
                self._log("[yellow]No active session to save[/yellow]")

        elif button_id == "btn-render":
            self._log("[cyan]Rendering preview...[/cyan]")
            if self.current_design and self.current_design.body_data:
                try:
                    path = render_preview.invoke(
                        {
                            "body_data": self.current_design.body_data,
                            "filename": f"preview_{self.current_design.iteration}",
                        }
                    )
                    self.current_design.snapshot_path = path
                    self._log(f"[green]Preview saved:[/green] {path}")
                except Exception as e:
                    self._log(f"[red]Render error:[/red] {str(e)}")
            else:
                self._log("[yellow]No design to render[/yellow]")

        elif button_id == "btn-toggle-preview":
            self.show_preview = not self.show_preview
            preview_area = self.query_one("#preview-area")
            preview_area.display = self.show_preview
            self._log(f"[cyan]Preview {'shown' if self.show_preview else 'hidden'}[/cyan]")

        elif button_id in ["btn-export-stl", "btn-export-step"]:
            if not self.current_design or not self.current_design.body_data:
                self._log("[yellow]No design to export[/yellow]")
                return

            fmt = "stl" if button_id == "btn-export-stl" else "step"
            export_path = self.project_path / "exports" / f"{self.current_design.name}.{fmt}"
            export_path.parent.mkdir(exist_ok=True)

            try:
                export_model.invoke(
                    {
                        "body_data": self.current_design.body_data,
                        "format": fmt,
                        "path": str(export_path),
                    }
                )
                self._log(f"[green]Exported:[/green] {export_path}")
            except Exception as e:
                self._log(f"[red]Export error:[/red] {str(e)}")

        elif button_id == "btn-history":
            history = self.design_history.get_history(limit=5)
            if history:
                self._log("[cyan]Recent History:[/cyan]")
                for iter in history:
                    self._log(f"  v{iter.version}: {iter.message}")
            else:
                self._log("[yellow]No design history[/yellow]")

        elif button_id == "btn-compare":
            self._log("[cyan]Use 'compare v1 v2' to compare versions[/cyan]")

    def action_quit(self) -> None:
        """Quit the application."""
        self._log("[cyan]Saving session...[/cyan]")
        if self.current_design:
            self.session_manager.save_session()
        self.exit()

    def action_clear_log(self) -> None:
        """Clear the log area."""
        self.query_one("#log-area", DesignLog).clear()

    def action_save_session(self) -> None:
        """Save the current session."""
        if self.current_design:
            self.session_manager.save_session()
            self._log("[green]Session saved![/green]")
        else:
            self._log("[yellow]No active session[/yellow]")

    def action_export(self) -> None:
        """Export current design."""
        if self.current_design:
            self._log("[cyan]Use Export STL/STEP buttons[/cyan]")
        else:
            self._log("[yellow]No design to export[/yellow]")

    def action_toggle_preview(self) -> None:
        """Toggle preview visibility."""
        self.show_preview = not self.show_preview
        preview_area = self.query_one("#preview-area")
        preview_area.display = self.show_preview

    def action_render_preview(self) -> None:
        """Render preview of current design."""
        if self.current_design and self.current_design.body_data:
            try:
                path = render_preview.invoke(
                    {
                        "body_data": self.current_design.body_data,
                        "filename": f"preview_{self.current_design.iteration}",
                    }
                )
                self.current_design.snapshot_path = path
                self._log(f"[green]Preview:[/green] {path}")
            except Exception as e:
                self._log(f"[red]Error:[/red] {str(e)}")
        else:
            self._log("[yellow]No design to render[/yellow]")


def run_tui(
    project_path: Path,
    model: Optional[str] = None,
    provider: str = "auto",
) -> None:
    """Run the interactive TUI.

    Args:
        project_path: Path to project directory
        model: LLM model to use
        provider: LLM provider
    """
    if not TEXTUAL_AVAILABLE:
        console.print(
            Panel.fit(
                "[bold red]Textual is required for TUI mode.[/bold red]\n\n"
                "Install with: pip install textual\n"
                "Or use CLI mode: planforge design [prompt]",
                title="TUI Not Available",
                border_style="red",
            )
        )
        return

    app = PlanForgeApp(
        project_path=project_path,
        model=model,
        provider=provider,
    )
    app.run()


if __name__ == "__main__":
    run_tui(Path.cwd())
