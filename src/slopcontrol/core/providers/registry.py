"""LLM Provider Registry - Unified client for PlanForge.

Two usage modes:

1. **Gateway mode** (recommended) – always talk to the local gateway::

       get_model()  →  ChatOpenAI(base_url="http://localhost:8000/v1")

2. **Direct mode** – instantiate providers directly (legacy)::

       get_model("openai:gpt-4o")  →  ChatOpenAI(...)

All new code should use the gateway; direct mode exists for backwards
compatibility and offline testing.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


def get_model(
    model: Optional[str] = None,
    provider: str = "gateway",
) -> "BaseChatModel":
    """Return a chat model instance.

    Args:
        model: Ignored in gateway mode. In direct mode: ``provider:model_name``.
        provider: ``"gateway"`` (default) or a concrete provider name for
                  direct instantiation.

    Returns:
        Configured LangChain chat model.
    """
    if provider == "gateway":
        return _create_gateway_client()

    # Legacy direct mode
    from .legacy import get_model_direct  # type: ignore[import-not-found]
    return get_model_direct(model, provider)


def _create_gateway_client() -> "BaseChatModel":
    """Create a LangChain client that always talks to the local gateway."""
    from langchain_openai import ChatOpenAI
    from slopcontrol.core.gateway.config import GatewayConfig

    cfg = GatewayConfig.from_env()
    base_url = f"{cfg.gateway_url}/v1"
    api_key = "slopcontrol-gateway-no-key"

    # Let user override via env just in case they want to skip the gateway
    base_url = os.environ.get("PLANFORGE_GATEWAY_URL", base_url)

    return ChatOpenAI(
        model="slopcontrol-gateway",
        api_key=api_key,
        base_url=base_url,
        temperature=0,
    )


def list_available_models(provider: Optional[str] = None) -> dict[str, list[str]]:
    """List available models for all providers.

    This is purely informational – the actual routing is handled by the
    gateway configuration (``PLANFORGE_LLM_CHAIN``).
    """
    all_models = {
        "kimi": [
            "moonshot-v1-8k",
            "moonshot-v1-32k",
            "moonshot-v1-128k",
        ],
        "qwen": [
            "qwen-max",
            "qwen-plus",
            "qwen-turbo",
        ],
        "glm": [
            "glm-4-plus",
            "glm-4-air",
            "glm-4-flash",
        ],
        "openai": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
        ],
        "grok": [
            "grok-3-beta",
            "grok-3-fast-beta",
        ],
        "ollama": [
            "llama3",
            "llama3.1",
            "mistral",
            "qwen2.5",
            "kimi-k2.6:cloud",
        ],
        "anthropic": [
            "claude-sonnet-4-7-20250620",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
        ],
        "ollama": [
            "llama3",
            "llama3.1",
            "mistral",
            "qwen2.5",
            "kimi-k2.6:cloud",
        ],
        "opencode": [
            "big-pickle",
        ],
    }

    if provider:
        return {provider: all_models.get(provider, [])}
    return all_models
