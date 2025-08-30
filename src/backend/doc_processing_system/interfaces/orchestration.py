"""
Orchestration interfaces.
"""

from abc import ABC, abstractmethod


class IWorkflowOrchestrator(ABC):
    """Interface for workflow orchestrators."""
    pass


class IAPIController(ABC):
    """Interface for API controllers."""
    pass