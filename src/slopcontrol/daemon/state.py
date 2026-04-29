"""Persistent state management for the SlopControl daemon.

Handles graceful shutdown/restore of all active project sessions, plans,
and knowledge graph deltas using SQLite. Supports session purge for recovery.
"""

from __future__ import annotations

import aiosqlite
import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """Persistent state for one project session."""
    project_name: str
    plan_version: str
    current_plan: dict[str, Any]
    conversation_history: list[dict[str, Any]]
    knowledge_deltas: list[dict[str, Any]]
    last_active: str
    status: str = "active"


class DaemonState:
    """Manages persistent daemon state across restarts."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or Path.home() / ".slopcontrol" / "daemon"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "state.db"
        self.sessions: dict[str, SessionState] = {}

    async def initialize(self) -> None:
        """Create database tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    project_name TEXT PRIMARY KEY,
                    state_json TEXT,
                    last_active TEXT
                )
            """)
            await db.commit()
            logger.info("Daemon state database initialized at %s", self.db_path)

    async def save_session(self, session: SessionState) -> None:
        """Persist a session state."""
        self.sessions[session.project_name] = session
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO sessions (project_name, state_json, last_active) VALUES (?, ?, ?)",
                (
                    session.project_name,
                    json.dumps(asdict(session)),
                    session.last_active,
                ),
            )
            await db.commit()
        logger.debug("Saved session for project: %s", session.project_name)

    async def load_all_sessions(self) -> dict[str, SessionState]:
        """Restore all sessions on daemon startup."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT state_json FROM sessions") as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    try:
                        data = json.loads(row[0])
                        session = SessionState(**data)
                        self.sessions[session.project_name] = session
                    except Exception as e:
                        logger.warning("Failed to restore session: %s", e)

        logger.info("Restored %d sessions from persistent storage", len(self.sessions))
        return self.sessions

    async def purge_session(self, project_name: str) -> bool:
        """Delete a session for clean restart."""
        if project_name in self.sessions:
            del self.sessions[project_name]

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM sessions WHERE project_name = ?",
                (project_name,),
            )
            await db.commit()

        logger.info("Purged session for project: %s", project_name)
        return True

    async def get_session(self, project_name: str) -> SessionState | None:
        """Retrieve a specific session."""
        return self.sessions.get(project_name)

    async def close(self) -> None:
        """Graceful shutdown - ensure all state is flushed."""
        # All state is already persisted on changes in this design
        logger.info("Daemon state saved. Shutting down gracefully.")
        # Additional cleanup can be added here (e.g. closing graph connections)
