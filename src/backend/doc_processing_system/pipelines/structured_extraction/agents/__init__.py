"""
Agents package for structured extraction demo.
Contains AI agent implementations.
"""

from .discovery import create_discovery_agent, SequentialDiscoveryDeps

__all__ = [
    "create_discovery_agent",
    "SequentialDiscoveryDeps"
]
