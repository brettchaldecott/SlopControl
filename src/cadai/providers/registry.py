"""LLM Provider Registry - Dynamic model loading for multiple providers."""

import os
from typing import Optional, Union

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama


SUPPORTED_PROVIDERS = {
    "openai": {
        "prefix": "openai:",
        "default_model": "gpt-4o",
    },
    "anthropic": {
        "prefix": "anthropic:",
        "default_model": "claude-sonnet-4-7",
    },
    "ollama": {
        "prefix": "ollama:",
        "default_model": "llama3",
    },
    "opencode": {
        "prefix": "opencode:",
        "default_model": "big-pickle",
    },
}


def parse_model_string(model_str: str) -> tuple[str, str]:
    """Parse model string to extract provider and model name.

    Args:
        model_str: Model string like "openai:gpt-4o" or just "gpt-4o"

    Returns:
        Tuple of (provider, model_name)
    """
    if ":" in model_str:
        provider, model = model_str.split(":", 1)
        return provider, model
    return "openai", model_str


def get_model(
    model: Optional[str] = None,
    provider: str = "auto",
) -> BaseChatModel:
    """Get a chat model instance based on configuration.

    Args:
        model: Model string (e.g., "openai:gpt-4o", "anthropic:claude-sonnet-4-7")
        provider: Provider hint if not in model string

    Returns:
        Configured chat model
    """
    if model is None:
        model = os.environ.get("CADAI_MODEL", "openai:gpt-4o")

    if ":" in model:
        parsed_provider, parsed_model = parse_model_string(model)
        return _create_model(parsed_provider, parsed_model)

    if provider == "auto":
        provider = _detect_provider(model)

    return _create_model(provider, model)


def _detect_provider(model: str) -> str:
    """Detect provider from model name patterns."""
    model_lower = model.lower()

    if any(x in model_lower for x in ["gpt", "o1", "o3", "o4"]):
        return "openai"
    if any(x in model_lower for x in ["claude", "sonnet", "haiku"]):
        return "anthropic"
    if any(x in model_lower for x in ["llama", "mistral", "codellama", "qwen"]):
        return "ollama"
    if any(x in model_lower for x in ["big-pickle", "opencode"]):
        return "opencode"

    return "openai"


def _create_model(provider: str, model: str) -> BaseChatModel:
    """Create a chat model for the specified provider."""
    provider = provider.lower()

    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=0,
        )

    elif provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        return ChatAnthropic(
            model=model,
            anthropic_api_key=api_key,
            temperature=0,
        )

    elif provider == "ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(
            model=model,
            base_url=base_url,
            temperature=0,
        )

    elif provider == "opencode":
        base_url = os.environ.get("OPENCODE_API_URL", "https://api.opencode.ai/v1")
        api_key = os.environ.get("OPENCODE_API_KEY")
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0,
        )

    else:
        raise ValueError(f"Unsupported provider: {provider}")


def list_available_models(provider: Optional[str] = None) -> dict[str, list[str]]:
    """List available models for providers.

    Args:
        provider: Specific provider to list, or None for all

    Returns:
        Dict mapping provider to list of model names
    """
    models = {
        "openai": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "o1-preview",
            "o1-mini",
        ],
        "anthropic": [
            "claude-sonnet-4-7-20250620",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-opus-4-5-20251114",
        ],
        "ollama": [
            "llama3",
            "llama3.1",
            "llama3.2",
            "mistral",
            "codellama",
            "qwen2.5",
        ],
        "opencode": [
            "big-pickle",
        ],
    }

    if provider:
        return {provider: models.get(provider, [])}
    return models
