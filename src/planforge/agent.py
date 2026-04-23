"""PlanForge Agent Factory - Creates CAD-enabled deep agents."""

import os
from pathlib import Path
from typing import Any, Literal, Optional, Union

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from .providers.registry import get_model
from .tools.cad import CAD_TOOLS


def create_cad_agent(
    model: Optional[Union[str, BaseChatModel]] = None,
    provider: str = "auto",
    project_dir: Optional[str] = None,
    auto_commit: bool = True,
    preview_on_iteration: bool = True,
    memory_path: Optional[str] = None,
    skills_path: Optional[str] = None,
    **deepagents_kwargs: Any,
) -> Any:
    """Create a CAD-enabled agent using the deepagents framework.

    Args:
        model: LLM model to use (e.g., "openai:gpt-4o", "anthropic:claude-sonnet-4-7")
               If None, uses PLANFORGE_MODEL env var or defaults to "openai:gpt-4o"
        provider: LLM provider to use ("openai", "anthropic", "ollama", "auto")
        project_dir: Directory for projects (default: ./projects or PLANFORGE_PROJECT_DIR)
        auto_commit: Whether to auto-commit design changes to git
        preview_on_iteration: Whether to render previews after design changes
        memory_path: Path to AGENTS.md memory file
        skills_path: Path to skills directory
        **deepagents_kwargs: Additional arguments passed to create_deep_agent

    Returns:
        Compiled LangGraph agent

    Example:
        >>> agent = create_cad_agent(model="openai:gpt-4o")
        >>> result = agent.invoke({"messages": [("user", "Create a 50mm cube")]})
    """
    if model is None:
        model = os.environ.get("PLANFORGE_MODEL", "opencode:big-pickle")

    if isinstance(model, str):
        chat_model = get_model(model, provider=provider)
    else:
        chat_model = model

    resolved_project_dir = project_dir or os.environ.get("PLANFORGE_PROJECT_DIR", "./projects")

    backend = FilesystemBackend(root_dir=resolved_project_dir)

    tools = list(CAD_TOOLS)

    memory_files = []
    if memory_path:
        memory_files.append(memory_path)
    else:
        default_memory = Path(__file__).parent / "memory" / "AGENTS.md"
        if default_memory.exists():
            memory_files.append(str(default_memory))

    skills_dirs = []
    if skills_path:
        skills_dirs.append(skills_path)
    else:
        default_skills = Path(__file__).parent / "skills"
        if default_skills.exists():
            skills_dirs.append(str(default_skills))

    system_prompt = deepagents_kwargs.pop(
        "system_prompt",
        """You are PlanForge, an expert 3D CAD designer. You help users create parametric 3D models
using natural language. You have access to llmcad for creating and modifying 3D geometry.

Key principles:
1. Always use millimeters (mm) as the unit of measurement
2. Start with simple shapes, then add complexity incrementally
3. Use named faces (top, bottom, front, back, left, right) for positioning
4. Verify designs with render_preview after major changes
5. Commit changes with descriptive messages after successful iterations

Available operations:
- Create shapes: Box, Cylinder, Sphere
- Create sketches: Rect, Circle, Ellipse, Polygon
- Operations: extrude, revolve, fillet, chamfer, shell, mirror
- Booleans: union, cut, intersect
- Export: step, stl, glb formats

Always explain what you're creating before doing it, and show previews.""",
    )

    agent = create_deep_agent(
        model=chat_model,
        tools=tools,
        system_prompt=system_prompt,
        backend=backend,
        memory=memory_files if memory_files else None,
        skills=skills_dirs if skills_dirs else None,
        **deepagents_kwargs,
    )

    return agent


def run_design_session(
    prompt: str,
    model: Optional[str] = None,
    provider: str = "auto",
    project_dir: Optional[str] = None,
    interactive: bool = True,
) -> dict[str, Any]:
    """Run a single design session with the CAD agent.

    Args:
        prompt: Design request from user
        model: LLM model to use
        provider: LLM provider
        project_dir: Project directory
        interactive: Whether to run interactively

    Returns:
        Agent response
    """
    agent = create_cad_agent(
        model=model,
        provider=provider,
        project_dir=project_dir,
    )

    messages = [HumanMessage(content=prompt)]

    if interactive:
        result = agent.invoke({"messages": messages}, stream=True)
        return {"agent": agent, "stream": result}
    else:
        result = agent.invoke({"messages": messages})
        return {"agent": agent, "result": result}
