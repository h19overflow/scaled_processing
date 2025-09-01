"""
Orchestration and system-wide messaging components.
Handles event routing, topic management, and cross-cutting concerns.
"""

from .kafka_topics_setup import KafkaTopicManager

__all__ = [
    "EventType", 
    "KafkaTopicManager"
]