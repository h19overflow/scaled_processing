"""
Evaluation interfaces.
"""

from abc import ABC, abstractmethod


class IQueryEngine(ABC):
    """Interface for query engines."""
    pass


class IEvaluator(ABC):
    """Interface for evaluators."""
    pass