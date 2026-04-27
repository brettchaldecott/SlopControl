"""Git operations for code domain projects.

Thin wrappers around gitpython, mirroring the CAD-domain git tools
so that every domain has a consistent VCS interface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from git import Repo
from langchain_core.tools import tool


def _get_repo(path: Optional[Path] = None) -> Optional[Repo]:
    if path is None:
        path = Path.cwd()
    try:
        return Repo(path)
    except Exception:
        return None


@tool
def init_git_repo(project_path: Optional[str] = None) -> str:
    """Initialise a git repository.

    Args:
        project_path: Directory to initialise.

    Returns:
        Confirmation message.
    """
    target = Path(project_path) if project_path else Path.cwd()
    try:
        Repo.init(target)
        return f"Initialised git repo at {target}"
    except Exception as exc:
        return f"Error: {exc}"


@tool
def commit(message: str, project_path: Optional[str] = None) -> str:
    """Stage all changes and commit.

    Args:
        message: Git commit message.
        project_path: Project directory.

    Returns:
        Short hash and confirmation.
    """
    repo = _get_repo(Path(project_path) if project_path else None)
    if repo is None:
        return "Error: Not a git repository"
    if not repo.is_dirty():
        return "Nothing to commit"
    try:
        repo.git.add(".")
        commit_obj = repo.index.commit(message)
        return f"Committed {commit_obj.hexsha[:8]}: {message}"
    except Exception as exc:
        return f"Error committing: {exc}"


@tool
def get_history(max_count: int = 10, project_path: Optional[str] = None) -> str:
    """Show recent git log.

    Args:
        max_count: Number of commits.
        project_path: Project directory.

    Returns:
        Formatted git log.
    """
    repo = _get_repo(Path(project_path) if project_path else None)
    if repo is None:
        return "Error: Not a git repository"
    try:
        commits = list(repo.iter_commits(max_count=max_count))
        lines = [f"{c.hexsha[:8]} {c.summary}" for c in commits]
        return "\n".join(lines)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def create_branch(name: str, project_path: Optional[str] = None) -> str:
    """Create and check out a new branch.

    Args:
        name: Branch name.
        project_path: Project directory.

    Returns:
        Confirmation.
    """
    repo = _get_repo(Path(project_path) if project_path else None)
    if repo is None:
        return "Error: Not a git repository"
    try:
        new = repo.create_head(name)
        new.checkout()
        return f"Created and checked out branch '{name}'"
    except Exception as exc:
        return f"Error: {exc}"


@tool
def merge_branch(name: str, project_path: Optional[str] = None) -> str:
    """Merge a branch into the current branch.

    Args:
        name: Branch to merge.
        project_path: Project directory.

    Returns:
        Confirmation or conflict warning.
    """
    repo = _get_repo(Path(project_path) if project_path else None)
    if repo is None:
        return "Error: Not a git repository"
    try:
        repo.git.merge(name)
        return f"Merged '{name}' into '{repo.active_branch.name}'"
    except Exception as exc:
        return f"Merge failed: {exc}"


GIT_TOOLS = [init_git_repo, commit, get_history, create_branch, merge_branch]
