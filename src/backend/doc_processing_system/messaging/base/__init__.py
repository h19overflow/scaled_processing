"""
Base classes for Kafka producers and consumers.
Provides common functionality for all messaging components.
"""

from .base_consumer import BaseKafkaConsumer
from .base_producer import BaseKafkaProducer

__all__ = [
    "BaseKafkaConsumer",
    "BaseKafkaProducer"
]