"""Interactive design session state management."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..utils.cad_helpers import deserialize_body


@dataclass
class DesignState:
    """Current state of a design session."""

    name: str
    body_data: Optional[str] = None
    body_name: Optional[str] = None
    model_info: dict = field(default_factory=dict)
    snapshot_path: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    iteration: int = 0
    history: list[dict] = field(default_factory=list)

    def update_body(self, body_data: str, name: str, model_info: dict) -> None:
        """Update the current body state."""
        self.body_data = body_data
        self.body_name = name
        self.model_info = model_info
        self.iteration += 1
        self.updated_at = datetime.now().isoformat()

        self.history.append(
            {
                "iteration": self.iteration,
                "timestamp": self.updated_at,
                "body_data": body_data,
                "name": name,
                "model_info": model_info,
            }
        )

    def get_body(self):
        """Get the actual body object."""
        if self.body_data:
            return deserialize_body(self.body_data).get("body")
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DesignState":
        """Create from dictionary."""
        return cls(**data)


class SessionManager:
    """Manages design sessions and state persistence."""

    def __init__(self, project_path: Path):
        """Initialize session manager.

        Args:
            project_path: Path to the project directory
        """
        self.project_path = project_path
        self.sessions_dir = project_path / ".planforge" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: Optional[DesignState] = None

    def create_session(self, name: str) -> DesignState:
        """Create a new design session.

        Args:
            name: Name for the session

        Returns:
            New DesignState
        """
        session_file = self.sessions_dir / f"{name}.json"

        if session_file.exists():
            return self.load_session(name)

        state = DesignState(name=name)
        self.current_session = state
        self._save_session(state)
        return state

    def load_session(self, name: str) -> Optional[DesignState]:
        """Load an existing session.

        Args:
            name: Session name

        Returns:
            DesignState or None
        """
        session_file = self.sessions_dir / f"{name}.json"

        if not session_file.exists():
            return None

        try:
            with open(session_file) as f:
                data = json.load(f)
            state = DesignState.from_dict(data)
            self.current_session = state
            return state
        except Exception:
            return None

    def save_session(self) -> None:
        """Save the current session."""
        if self.current_session:
            self._save_session(self.current_session)

    def _save_session(self, state: DesignState) -> None:
        """Internal save session."""
        session_file = self.sessions_dir / f"{state.name}.json"
        with open(session_file, "w") as f:
            json.dump(state.to_dict(), f, indent=2)

    def list_sessions(self) -> list[str]:
        """List all saved sessions.

        Returns:
            List of session names
        """
        sessions = []
        for file in self.sessions_dir.glob("*.json"):
            sessions.append(file.stem)
        return sorted(sessions)

    def delete_session(self, name: str) -> bool:
        """Delete a session.

        Args:
            name: Session name

        Returns:
            True if deleted, False if not found
        """
        session_file = self.sessions_dir / f"{name}.json"
        if session_file.exists():
            session_file.unlink()
            if self.current_session and self.current_session.name == name:
                self.current_session = None
            return True
        return False

    def get_current_session(self) -> Optional[DesignState]:
        """Get the current session."""
        return self.current_session

    def export_state(self, name: str, output_path: Path) -> None:
        """Export session state to a file.

        Args:
            name: Session name
            output_path: Path to export to
        """
        state = self.load_session(name)
        if state:
            with open(output_path, "w") as f:
                json.dump(state.to_dict(), f, indent=2)

    def import_state(self, input_path: Path) -> Optional[DesignState]:
        """Import session state from a file.

        Args:
            input_path: Path to import from

        Returns:
            Imported DesignState
        """
        with open(input_path) as f:
            data = json.load(f)
        state = DesignState.from_dict(data)
        self._save_session(state)
        self.current_session = state
        return state
