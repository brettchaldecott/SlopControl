"""PlanForge domain plugin foundation.

Provides ``DomainPlugin`` and ``DomainSession`` base classes plus the
``create_domain_agent`` factory.
"""

from .plugin import DomainPlugin
from .session import DomainSession
from .agent_factory import create_domain_agent

__all__ = ["DomainPlugin", "DomainSession", "create_domain_agent"]
