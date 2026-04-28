"""Auto-discovery of local LLM servers.

Probes common local ports on startup and injects working models into the
fallback chain.  This lets PlanForge use LM Studio, vLLM, llama.cpp, etc.
without manual configuration.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import anyio

from .config import GatewayConfig
from .router import ProviderRoute

logger = logging.getLogger(__name__)

LOCAL_PORTS: dict[str, int] = {
    "ollama": 11434,
    "lmstudio": 1234,
    "vllm": 8000,
    "llamacpp": 8080,
    "tabbyapi": 5000,
}

CACHE_FILE = Path.home() / ".slopcontrol" / "local_routes.json"


async def discover_local_providers(
    timeout: float = 2.0, use_cache: bool = True
) -> list[ProviderRoute]:
    """Probe known local ports and return working routes.

    Args:
        timeout: Seconds to wait per probe.
        use_cache: If True, prefer cached routes from a previous run
                   and only re-probe the remainder.
    """
    routes: list[ProviderRoute] = []

    if use_cache:
        cached = _load_cache()
        if cached:
            logger.info("Loaded %d local routes from cache", len(cached))
            routes.extend(cached)

    # Determine which ports still need probing
    cached_names = {r.provider for r in routes}
    to_probe = {n: p for n, p in LOCAL_PORTS.items() if n not in cached_names}

    if not to_probe:
        return routes

    async with anyio.create_task_group() as tg:
        results: dict[str, ProviderRoute | None] = {}

        async def _wrapper(name: str, port: int) -> None:
            results[name] = await _probe_one(name, port, timeout)

        for name, port in to_probe.items():
            tg.start_soon(_wrapper, name, port)

    new_routes = [r for r in results.values() if r is not None]
    _save_cache(routes + new_routes)
    return routes + new_routes


async def _probe_one(name: str, port: int, timeout: float) -> ProviderRoute | None:
    """Try to talk to a local server via HTTP."""
    base_url = f"http://localhost:{port}"

    # Probe strategies: list models first
    paths = ["/v1/models", "/api/tags", "/models", "/health"]
    for path in paths:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                resp = await client.get(base_url + path)
                if resp.status_code < 500:  # Any response means the server is alive
                    logger.info(
                        "Discovered local provider %s on port %d (%s = %d)",
                        name, port, path, resp.status_code,
                    )
                    return ProviderRoute(
                        provider=name,
                        model=name,  # User can override via chain spec
                        base_url=base_url + "/v1",
                        api_key=None,
                    )
        except Exception as exc:
            logger.debug("Probe %s:%d path=%s failed: %s", name, port, path, exc)
            continue

    logger.debug("No response from %s on port %d", name, port)
    return None


def _load_cache() -> list[ProviderRoute]:
    if not CACHE_FILE.exists():
        return []
    try:
        data = json.loads(CACHE_FILE.read_text())
        return [ProviderRoute(**item) for item in data]
    except Exception as exc:
        logger.warning("Failed to load local route cache: %s", exc)
        return []


def _save_cache(routes: list[ProviderRoute]) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(
            json.dumps(
                [
                    {"provider": r.provider, "model": r.model, "base_url": r.base_url, "api_key": r.api_key}
                    for r in routes
                ],
                indent=2,
            )
        )
    except Exception as exc:
        logger.warning("Failed to save local route cache: %s", exc)
