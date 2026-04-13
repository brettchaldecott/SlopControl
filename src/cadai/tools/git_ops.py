"""Git operations for automatic version control of designs."""

import os
from pathlib import Path
from typing import Optional

from git import Repo, Commit
from langchain_core.tools import tool


def _get_git_repo(path: Optional[Path] = None) -> Optional[Repo]:
    """Get git repository for path."""
    if path is None:
        path = Path.cwd()

    try:
        return Repo(path)
    except Exception:
        return None


@tool
def commit_design(
    message: str,
    project_path: Optional[str] = None,
    tags: Optional[str] = None,
) -> str:
    """Commit current design state to git.

    Args:
        message: Commit message describing changes
        project_path: Path to the project (default: current directory)
        tags: Comma-separated tags for the commit

    Returns:
        Commit hash and confirmation message
    """
    repo_path = Path(project_path) if project_path else Path.cwd()
    repo = _get_git_repo(repo_path)

    if repo is None:
        return "Error: Not a git repository. Run 'git init' first."

    if repo.is_dirty():
        repo.index.commit(message)

        if tags:
            tag_list = [t.strip() for t in tags.split(",")]
            for tag in tag_list:
                repo.create_tag(tag)

        return f"Committed: {repo.head.commit.hexsha[:8]} - {message}"

    return "No changes to commit."


@tool
def get_design_history(
    project_path: Optional[str] = None,
    max_count: int = 10,
) -> str:
    """Get the design version history.

    Args:
        project_path: Path to the project
        max_count: Maximum number of commits to show

    Returns:
        Formatted commit history
    """
    repo_path = Path(project_path) if project_path else Path.cwd()
    repo = _get_git_repo(repo_path)

    if repo is None:
        return "Error: Not a git repository."

    commits = list(repo.iter_commits(max_count=max_count))

    if not commits:
        return "No commits yet."

    lines = ["Design History:", "=" * 60]

    for i, commit in enumerate(commits):
        short_hash = commit.hexsha[:8]
        author = commit.author.name
        date = commit.committed_datetime.strftime("%Y-%m-%d %H:%M")
        message = commit.message.strip().split("\n")[0]

        lines.append(f"{i + 1}. {short_hash} | {date}")
        lines.append(f"   {message}")
        lines.append(f"   by {author}")
        lines.append("")

    return "\n".join(lines)


@tool
def restore_version(
    commit_hash: str,
    project_path: Optional[str] = None,
) -> str:
    """Restore design to a previous version.

    Args:
        commit_hash: Full or partial commit hash
        project_path: Path to the project

    Returns:
        Confirmation message
    """
    repo_path = Path(project_path) if project_path else Path.cwd()
    repo = _get_git_repo(repo_path)

    if repo is None:
        return "Error: Not a git repository."

    try:
        commit = repo.commit(commit_hash)
        repo.git.checkout(commit)
        return (
            f"Restored to version: {commit.hexsha[:8]} - {commit.message.strip().split(chr(10))[0]}"
        )
    except Exception as e:
        return f"Error restoring version: {str(e)}"


@tool
def create_experiment_branch(
    branch_name: str,
    project_path: Optional[str] = None,
) -> str:
    """Create a new branch for experimental designs.

    Args:
        branch_name: Name for the new branch
        project_path: Path to the project

    Returns:
        Confirmation message
    """
    repo_path = Path(project_path) if project_path else Path.cwd()
    repo = _get_git_repo(repo_path)

    if repo is None:
        return "Error: Not a git repository."

    if branch_name in repo.branches:
        repo.heads[branch_name].checkout()
        return f"Switched to existing branch: {branch_name}"

    new_branch = repo.create_head(branch_name)
    new_branch.checkout()
    return f"Created and switched to new branch: {branch_name}"


@tool
def merge_experiment(
    branch_name: str,
    project_path: Optional[str] = None,
    delete_branch: bool = True,
) -> str:
    """Merge an experimental branch back to main.

    Args:
        branch_name: Branch to merge
        project_path: Path to the project
        delete_branch: Whether to delete the branch after merging

    Returns:
        Confirmation message
    """
    repo_path = Path(project_path) if project_path else Path.cwd()
    repo = _get_git_repo(repo_path)

    if repo is None:
        return "Error: Not a git repository."

    try:
        repo.heads.main.checkout()
        repo.git.merge(branch_name)

        if delete_branch and branch_name in repo.branches:
            repo.delete_head(branch_name)

        return f"Successfully merged {branch_name} into main"
    except Exception as e:
        return f"Error merging branch: {str(e)}"


@tool
def init_git_repo(
    project_path: Optional[str] = None,
) -> str:
    """Initialize a git repository for a project.

    Args:
        project_path: Path to initialize (default: current directory)

    Returns:
        Confirmation message
    """
    repo_path = Path(project_path) if project_path else Path.cwd()

    if _get_git_repo(repo_path):
        return "Git repository already exists."

    Repo.init(repo_path)

    repo = Repo(repo_path)
    config_writer = repo.config_writer()
    config_writer.set_value("user", "name", "CadAI Agent").release()
    config_writer.set_value("user", "email", "cadai@agent.local").release()

    gitignore_path = repo_path / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text("""__pycache__/
*.pyc
*.pyo
*.egg-info/
.eggs/
dist/
build/
*.egg
.env
.venv/
venv/
*.stl
*.step
*.glb
*.png
projects/
""")

    repo.index.add([".gitignore"])
    repo.index.commit("Initial commit: CadAI project setup")

    return f"Initialized git repository at {repo_path}"


GIT_TOOLS = [
    commit_design,
    get_design_history,
    restore_version,
    create_experiment_branch,
    merge_experiment,
    init_git_repo,
]
