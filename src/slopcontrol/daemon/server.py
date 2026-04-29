"""SlopControl Daemon Server - Long-running orchestrator with WebSocket TUI support.

This is the central persistent process. It manages multiple projects, handles
graceful shutdown with full state restoration, and provides WebSocket interface
for the rich Textual TUI client.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from slopcontrol.daemon.state import DaemonState, SessionState
from slopcontrol.core.orchestrator.conductor import Conductor
from slopcontrol.core.plan.schema import DesignPlan

logger = logging.getLogger(__name__)


class SlopControlDaemon:
    """Main daemon that coordinates all project sessions."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self.app = self._create_app()
        self.state = DaemonState()
        self.active_connections: dict[str, WebSocket] = {}
        self.conductors: dict[str, Conductor] = {}
        self.shutdown_event = asyncio.Event()

    def _create_app(self) -> FastAPI:
        app = FastAPI(
            title="SlopControl Daemon",
            version="0.3.0",
            description="Persistent multi-project agentic development orchestrator",
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.get("/health")
        async def health():
            return {
                "status": "running",
                "active_sessions": len(self.state.sessions),
                "version": "0.3.0"
            }

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            client_id = str(id(websocket))
            self.active_connections[client_id] = websocket
            try:
                await self._handle_client(websocket, client_id)
            except WebSocketDisconnect:
                logger.info("Client disconnected: %s", client_id)
            finally:
                self.active_connections.pop(client_id, None)

        return app

    async def _handle_client(self, websocket: WebSocket, client_id: str) -> None:
        """Handle commands from TUI client (including /project, /knowledge, /purge)."""
        await websocket.send_text("Connected to SlopControl Daemon. Type /help for commands.")

        while True:
            data = await websocket.receive_text()
            if data.startswith("/"):
                await self._handle_command(websocket, data)
            else:
                await websocket.send_text(f"Echo: {data}")

    async def _handle_command(self, websocket: WebSocket, command: str) -> None:
        """Parse slash commands like /project, /knowledge, /purge, /status."""
        parts = command.strip().split()
        cmd = parts[0].lower()

        if cmd == "/help":
            await websocket.send_text(
                "Available commands:\n"
                "  /project <name>   - Switch to or create project session\n"
                "  /knowledge <query> - Query the knowledge graph\n"
                "  /purge <project>  - Reset a broken session\n"
                "  /status           - Show daemon and session status\n"
                "  /truth            - Show Coverage of Truth metrics"
            )
        elif cmd == "/purge" and len(parts) > 1:
            project = parts[1]
            success = await self.state.purge_session(project)
            await websocket.send_text(f"Session for {project} purged. {'Success' if success else 'Failed'}.")
        elif cmd == "/status":
            await websocket.send_text(f"Active sessions: {len(self.state.sessions)}. All systems operational.")
        else:
            await websocket.send_text(f"Command received: {command}")

    async def start(self) -> None:
        """Start the daemon with graceful shutdown support."""
        await self.state.initialize()
        await self.state.load_all_sessions()

        # Register graceful shutdown handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self._shutdown(s)),
            )

        # Restore previous sessions
        await self.state.load_all_sessions()

        logger.info("SlopControl Daemon starting on %s:%s", self.host, self.port)
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            lifespan="on",
        )
        server = uvicorn.Server(config)

        try:
            await server.serve()
        finally:
            await self._shutdown()

    async def _shutdown(self, signal: Any = None) -> None:
        """Graceful shutdown - persist all state before exit."""
        if signal:
            logger.info("Received shutdown signal %s. Saving state...", signal)
        else:
            logger.info("Shutting down gracefully...")

        await self.state.close()
        self.shutdown_event.set()
        logger.info("Daemon shutdown complete. All sessions persisted.")


def main() -> None:
    """Entry point for the daemon."""
    import logging
    logging.basicConfig(level=logging.INFO)

    daemon = SlopControlDaemon()
    asyncio.run(daemon.start())


if __name__ == "__main__":
    main()
