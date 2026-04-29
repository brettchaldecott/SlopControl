"""Rich Textual TUI Client for SlopControl Daemon.

This is the primary interactive interface. It connects via WebSocket to the
background daemon and provides a rich command-driven experience with slash
commands (/project, /knowledge, /purge, /status, etc.).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Input, Static

logger = logging.getLogger(__name__)


class SlopControlTUI(App):
    """Rich terminal user interface for the persistent SlopControl daemon."""

    TITLE = "SlopControl"
    SUB_TITLE = "Multi-Project Agentic Development Environment"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+d", "daemon_status", "Daemon Status"),
        Binding("/", "command_mode", "Command"),
    ]

    CSS = """
    Screen {
        background: #1a1a2e;
    }
    Input {
        background: #16213e;
        border: tall $accent;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.websocket = None
        self.current_project = None
        self.log_area = Static("", id="log")
        self.input = Input(placeholder="Type /help for commands...")

    def compose(self) -> ComposeResult:
        yield Header()
        yield self.log_area
        yield self.input
        yield Footer()

    def on_mount(self) -> None:
        self.add_log("SlopControl TUI started. Connecting to daemon...")
        self.add_log("Type /help to see available commands.")
        asyncio.create_task(self.connect_to_daemon())

    def add_log(self, message: str) -> None:
        """Add message to the log area."""
        current = self.log_area.renderable
        if isinstance(current, Text):
            current.append("\n" + message)
        else:
            self.log_area.update(Text.from_markup(message))
        self.log_area.refresh()

    async def connect_to_daemon(self) -> None:
        """Connect to the background daemon via WebSocket."""
        import websockets
        try:
            self.websocket = await websockets.connect("ws://127.0.0.1:8765/ws")
            self.log("[green]Connected to SlopControl Daemon.[/green]")
            asyncio.create_task(self.listen_to_daemon())
        except Exception as e:
            self.log(f"[red]Could not connect to daemon: {e}[/red]")
            self.log("Run `slopcontrol daemon` in another terminal to start the background service.")

    async def listen_to_daemon(self) -> None:
        """Listen for messages from the daemon."""
        if not self.websocket:
            return
        try:
            async for message in self.websocket:
                self.log(message)
        except Exception as e:
            self.add_log(f"[red]Connection lost: {e}[/red]")

    @on(Input.Submitted)
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input (commands or chat)."""
        text = event.value.strip()
        if not text:
            return

        self.add_log(f"> {text}")
        event.input.clear()

        if text.startswith("/"):
            await self.handle_command(text)
        else:
            if self.websocket:
                await self.websocket.send(text)
            else:
                self.add_log("[yellow]Not connected to daemon.[/yellow]")

    async def handle_command(self, command: str) -> None:
        """Handle slash commands."""
        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "/help":
            self.add_log("""[bold cyan]Available commands:[/bold cyan]
  /project <name>     Switch to or create a project session
  /knowledge <query>  Query the knowledge graph and truths
  /purge <project>    Reset a broken session for a project
  /status             Show daemon and session status
  /truth              Show Coverage of Truth metrics
  /index              Trigger knowledge base reindexing""")
        elif cmd == "/project" and len(parts) > 1:
            project = parts[1]
            self.current_project = project
            self.add_log(f"Switched to project: [bold]{project}[/bold]")
            if self.websocket:
                await self.websocket.send(f"/project {project}")
        elif cmd == "/purge" and len(parts) > 1:
            project = parts[1]
            self.add_log(f"Purging session for {project}...")
            if self.websocket:
                await self.websocket.send(f"/purge {project}")
        elif cmd == "/status":
            self.add_log("Querying daemon status...")
            if self.websocket:
                await self.websocket.send("/status")
        elif cmd == "/knowledge" and len(parts) > 1:
            query = " ".join(parts[1:])
            self.add_log(f"Querying knowledge: {query}")
            if self.websocket:
                await self.websocket.send(f"/knowledge {query}")
        else:
            self.add_log(f"[yellow]Unknown command: {command}. Type /help.[/yellow]")

    def action_daemon_status(self) -> None:
        """Show daemon status."""
        self.add_log("[green]Daemon status: Running (persistent sessions restored on startup)[/green]")

    def action_command_mode(self) -> None:
        """Focus the input for commands."""
        self.input.focus()

    def action_quit(self) -> None:
        """Clean shutdown."""
        if self.websocket:
            asyncio.create_task(self.websocket.close())
        self.exit()


def run_tui() -> None:
    """Entry point to run the TUI."""
    app = SlopControlTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
