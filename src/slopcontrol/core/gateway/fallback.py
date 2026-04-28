"""Fallback retry logic for resilient LLM requests.

Tries each provider in the configured chain until one succeeds,
catching rate limits, connection errors, and transient failures.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

if TYPE_CHECKING:
    from .config import GatewayConfig
    from .router import ProviderRoute

logger = logging.getLogger(__name__)

# Exceptions that are worth retrying on a different provider
_RETRYABLE_EXCEPTIONS: tuple = (
    Exception,  # broad for now; tighten later
)


def instantiate_model(route: ProviderRoute, temperature: float = 0) -> BaseChatModel:
    """Create a LangChain model from a resolved provider route.

    * OpenAI-compatible endpoints → ``ChatOpenAI`` with custom ``base_url``.
    * Anthropic                → ``ChatAnthropic``.
    * Ollama                  → ``ChatOllama``.
    """
    provider = route.provider.lower()

    if provider == "ollama":
        return ChatOllama(
            model=route.model,
            base_url=route.base_url or "http://localhost:11434",
            temperature=temperature,
        )

    # Default: OpenAI-compatible endpoint (includes Grok, OpenAI, Kimi, Qwen, GLM)
    if not route.api_key:
        raise RuntimeError(f"API key missing for provider {provider}, model {route.model}")
    if not route.base_url:
        raise RuntimeError(f"Base URL missing for provider {provider}, model {route.model}")

    return ChatOpenAI(
        model=route.model,
        api_key=route.api_key,
        base_url=route.base_url,
        temperature=temperature,
    )


class FallbackChain:
    """Ordered list of providers with retry logic.

    Use ``invoke()`` or ``ainvoke()`` to send a request, automatically
    walking down the chain on failure.
    """

    def __init__(self, routes: list[ProviderRoute], temperature: float = 0) -> None:
        self.routes = routes
        self.temperature = temperature

    def invoke(self, messages: list[BaseMessage], **kwargs: Any) -> BaseMessage:
        """Synchronous chat completion with fallback."""
        last_error: Exception | None = None
        for idx, route in enumerate(self.routes):
            try:
                model = instantiate_model(route, self.temperature)
                return model.invoke(messages, **kwargs)
            except Exception as exc:
                logger.warning(
                    "Provider %s (%s) failed: %s",
                    route.provider,
                    route.model,
                    exc,
                )
                last_error = exc
                continue
        raise RuntimeError(
            f"All {len(self.routes)} providers exhausted. Last error: {last_error}"
        ) from last_error

    async def ainvoke(self, messages: list[BaseMessage], **kwargs: Any) -> BaseMessage:
        """Asynchronous chat completion with fallback."""
        last_error: Exception | None = None
        for idx, route in enumerate(self.routes):
            try:
                model = instantiate_model(route, self.temperature)
                return await model.ainvoke(messages, **kwargs)
            except Exception as exc:
                logger.warning(
                    "Provider %s (%s) failed: %s",
                    route.provider,
                    route.model,
                    exc,
                )
                last_error = exc
                continue
        raise RuntimeError(
            f"All {len(self.routes)} providers exhausted. Last error: {last_error}"
        ) from last_error


def create_fallback_chain(
    config: GatewayConfig,
    temperature: float = 0,
) -> FallbackChain:
    """Build a ``FallbackChain`` from global gateway config."""
    from .router import parse_chain, build_routes

    parsed = parse_chain(config.llm_chain)
    routes = build_routes(parsed, config)
    return FallbackChain(routes, temperature=temperature)
