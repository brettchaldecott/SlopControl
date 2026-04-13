"""File operations tools for project management."""

from pathlib import Path
from typing import Optional

from langchain_core.tools import tool


@tool
def save_design_state(
    body_data: str,
    name: str,
    project_path: Optional[str] = None,
) -> str:
    """Save the current design state to a file.

    Args:
        body_data: JSON data containing the body
        name: Design name (without extension)
        project_path: Path to the project directory

    Returns:
        Path to saved file
    """
    import json

    project = Path(project_path) if project_path else Path.cwd()
    designs_dir = project / "designs"
    designs_dir.mkdir(parents=True, exist_ok=True)

    design_file = designs_dir / f"{name}.json"
    design_file.write_text(body_data)

    return str(design_file)


@tool
def load_design_state(
    name: str,
    project_path: Optional[str] = None,
) -> str:
    """Load a saved design state.

    Args:
        name: Design name (without .json extension)
        project_path: Path to the project directory

    Returns:
        JSON data containing the body
    """
    project = Path(project_path) if project_path else Path.cwd()
    design_file = project / "designs" / f"{name}.json"

    if not design_file.exists():
        return f"Error: Design '{name}' not found"

    return design_file.read_text()


@tool
def list_designs(
    project_path: Optional[str] = None,
) -> str:
    """List all saved designs in a project.

    Args:
        project_path: Path to the project directory

    Returns:
        List of design names
    """
    project = Path(project_path) if project_path else Path.cwd()
    designs_dir = project / "designs"

    if not designs_dir.exists():
        return "No designs saved yet."

    designs = sorted(design.stem for design in designs_dir.glob("*.json"))

    if not designs:
        return "No designs saved yet."

    return "Saved designs:\n" + "\n".join(f"  - {name}" for name in designs)


@tool
def create_project(
    project_name: str,
    project_path: Optional[str] = None,
) -> str:
    """Create a new CadAI project directory.

    Args:
        project_name: Name for the new project
        project_path: Parent directory (default: current directory)

    Returns:
        Confirmation message with project path
    """
    parent = Path(project_path) if project_path else Path.cwd()
    project_dir = parent / project_name

    if project_dir.exists():
        return f"Project '{project_name}' already exists at {project_dir}"

    project_dir.mkdir(parents=True)

    (project_dir / "designs").mkdir()
    (project_dir / "exports").mkdir()
    (project_dir / "previews").mkdir()

    readme = project_dir / "README.md"
    readme.write_text(f"""# {project_name}

A CadAI project for designing 3D parts.

## Structure
- `designs/` - Saved design states
- `exports/` - Exported CAD files (STEP, STL, GLB)
- `previews/` - Rendered preview images

## Usage
Use the CadAI CLI to work with this project:
```bash
cadai design --project {project_name}
```
""")

    return f"Created project '{project_name}' at {project_dir}"


@tool
def delete_design(
    name: str,
    project_path: Optional[str] = None,
    confirm: bool = False,
) -> str:
    """Delete a saved design.

    Args:
        name: Design name to delete
        project_path: Path to the project
        confirm: Must be True to actually delete

    Returns:
        Confirmation or error message
    """
    if not confirm:
        return f"Warning: This will delete '{name}'. Set confirm=True to proceed."

    project = Path(project_path) if project_path else Path.cwd()
    design_file = project / "designs" / f"{name}.json"

    if not design_file.exists():
        return f"Error: Design '{name}' not found"

    design_file.unlink()
    return f"Deleted design: {name}"


FILE_OPS_TOOLS = [
    save_design_state,
    load_design_state,
    list_designs,
    create_project,
    delete_design,
]
