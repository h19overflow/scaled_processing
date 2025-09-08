"""
Agents package for structured extraction demo.
Contains AI agent implementations.
"""

from .discovery import create_discovery_agent, SequentialDiscoveryDeps
from .consolidation import create_consolidation_agent, ConsolidationDeps

__all__ = [
    "create_discovery_agent",
    "create_consolidation_agent",
    "SequentialDiscoveryDeps",
    "ConsolidationDeps"
]
