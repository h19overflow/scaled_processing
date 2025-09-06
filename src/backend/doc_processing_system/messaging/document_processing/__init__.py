"""
Simple document processing messaging.
Process documents and handle Kafka events without unnecessary abstractions.
"""

from .document_processor import DocumentProcessor
from .kafka_handler import KafkaHandler

__all__ = [
    "DocumentProcessor",
    "KafkaHandler"
]