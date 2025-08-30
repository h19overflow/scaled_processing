"""
Agent interfaces from the class diagram.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from .models import IDocument


class BaseAgent(ABC):
    """Base interface for all agents."""
    pass


class IImageAgent(BaseAgent):
    """Interface for Image Agent - Visual Analyzer."""
    pass


class IOrchestratorAgent(BaseAgent):
    """Interface for Orchestrator Agent - Schema Creator."""
    pass


class IFieldDiscoveryAgent(BaseAgent):
    """Interface for Field Discovery Agent."""
    pass


class IExtractionAgent(BaseAgent):
    """Interface for Extraction Agent - Worker Swarm."""
    pass