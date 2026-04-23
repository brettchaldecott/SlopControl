"""Provider routing logic for the LLM gateway.

Maps incoming model names to upstream providers and their
OpenAI-compatible endpoint configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import GatewayConfig


@dataclass(frozen=True)
class ProviderRoute:
    """Resolved route for a single model."""

    provider: str          # e.g. "kimi", "qwen", "glm", "openai"
    model: str             # e.g. "moonshot-v1-8k"
    base_url: str | None   # OpenAI-compatible base URL
    api_key: str | None    # API key for this provider


def parse_model_string(model_str: str) -> tuple[str, str]:
    """Split ``provider:model`` into (provider, model).

    If no colon, treat the whole string as a model name
    and return provider as the literal ``"unknown"``.
    """
    if ":" in model_str:
        provider, model = model_str.split(":", 1)
        return provider.strip(), model.strip()
    return "unknown", model_str.strip()


def parse_chain(chain: str) -> list[tuple[str, str]]:
    """Parse a comma-separated fallback chain into ordered list.

    >>> parse_chain("kimi:moonshot-v1-8k,qwen:qwen-max")
    [("kimi", "moonshot-v1-8k"), ("qwen", "qwen-max")]
    """
    entries: list[tuple[str, str]] = []
    for entry in chain.split(","):
        entry = entry.strip()
        if not entry:
            continue
        entries.append(parse_model_string(entry))
    return entries


def build_routes(
    chain: list[tuple[str, str]],
    config: GatewayConfig,
) -> list[ProviderRoute]:
    """Convert parsed chain into fully resolved ``ProviderRoute`` objects."""
    routes: list[ProviderRoute] = []
    for provider, model in chain:
        # Handle anthropic separately — it is **not** OpenAI-compatible
        if provider.lower() == "anthropic":
            routes.append(
                ProviderRoute(
                    provider=provider,
                    model=model,
                    base_url=None,
                    api_key=config.get_provider_api_key("anthropic"),
                )
            )
            continue

        # Handle ollama separately — uses LangChain ChatOllama
        if provider.lower() == "ollama":
            routes.append(
                ProviderRoute(
                    provider=provider,
                    model=model,
                    base_url=config.ollama_base_url,
                    api_key=None,
                )
            )
            continue

        # Everything else is an OpenAI-compatible endpoint (ChatOpenAI with custom base_url)
        base_url = config.get_provider_base_url(provider) or config.openai_api_url
        api_key = config.get_provider_api_key(provider)
        routes.append(
            ProviderRoute(
                provider=provider,
                model=model,
                base_url=base_url,
                api_key=api_key,
            )
        )
    return routes
