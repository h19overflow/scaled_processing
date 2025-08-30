"""
Messaging interfaces.
"""

from abc import ABC, abstractmethod


class IEventPublisher(ABC):
    """Interface for event publishers."""
    pass


class IEventConsumer(ABC):
    """Interface for event consumers."""
    pass