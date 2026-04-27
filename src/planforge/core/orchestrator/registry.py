"""Plugin registry with auto-discovery."""

from __future__ import annotations

import importlib
import inspect
import logging
from pathlib import Path
from typing import Any

from planforge.core.domain_base.plugin import DomainPlugin

logger = logging.getLogger(__name__)

_DEFAULT_PACKAGES = [
    "planforge.domains.cad",
    "planforge.domains.code",
]


class PluginRegistry:
    """Central registry for :class:`DomainPlugin` implementations.

    Supports both manual registration (:meth:`register`) and
    automatic discovery (:meth:`auto_discover`) from known packages.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, DomainPlugin] = {}

    # -- Registration -------------------------------------------------

    def register(self, plugin: DomainPlugin) -> None:
        """Add a domain plugin manually."""
        if not isinstance(plugin, DomainPlugin):
            raise TypeError(f"Expected DomainPlugin, got {type(plugin)}")
        self._plugins[plugin.name] = plugin
        logger.info("Registered domain plugin: %s", plugin.name)

    def get(self, name: str) -> DomainPlugin:
        """Retrieve a plugin by its short name (e.g. ``"cad"``)."""
        if name not in self._plugins:
            raise KeyError(f"No plugin registered for domain '{name}'")
        return self._plugins[name]

    def has(self, name: str) -> bool:
        return name in self._plugins

    def list_domains(self) -> list[str]:
        return sorted(self._plugins.keys())

    def all(self) -> dict[str, DomainPlugin]:
        return dict(self._plugins)

    # -- Auto-discovery -------------------------------------------------

    def auto_discover(
        self,
        packages: list[str] | None = None,
    ) -> int:
        """Scan packages for ``DomainPlugin`` subclasses and auto-register.

        Args:
            packages: Packages to scan (default: built-in domain packages).

        Returns:
            Number of plugins discovered.
        """
        targets = packages or _DEFAULT_PACKAGES
        count = 0
        for pkg_name in targets:
            try:
                mod = importlib.import_module(pkg_name)
                for _name, obj in inspect.getmembers(mod, inspect.isclass):
                    if (
                        issubclass(obj, DomainPlugin)
                        and obj is not DomainPlugin
                        and not inspect.isabstract(obj)
                    ):
                        instance = obj()
                        if instance.name not in self._plugins:
                            self.register(instance)
                            count += 1
            except Exception as exc:
                logger.warning("Auto-discovery failed for %s: %s", pkg_name, exc)
        return count

    # -- External adapters ----------------------------------------------

    def get_external_adapter(self, name: str) -> Any | None:
        """Return an external adapter by name (e.g. ``"opencode"``, ``"claude"``)."""
        # Lazy import to avoid circular deps
        from planforge.integrations.opencode import OpenCodeAdapter
        from planforge.integrations.claude import ClaudeAdapter
        from planforge.integrations.cursor import CursorAdapter

        mapping: dict[str, Any] = {
            "opencode": OpenCodeAdapter(),
            "claude": ClaudeAdapter(),
            "cursor": CursorAdapter(),
        }
        return mapping.get(name)
