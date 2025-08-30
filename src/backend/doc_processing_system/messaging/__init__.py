"""
Messaging package for Kafka producers and consumers.
Provides event-driven communication between system components.
"""

# Base classes
from .base_producer import BaseKafkaProducer
from .base_consumer import BaseKafkaConsumer

# Specific producers
from .document_producer import DocumentProducer
from .rag_producer import RAGProducer
from .extraction_producer import ExtractionProducer
from .query_producer import QueryProducer

# Specific consumers  
from .document_consumer import DocumentConsumer, create_simple_document_consumer

# Event bus
from .event_bus import EventBus, EventType, create_event_bus, get_all_event_types

__all__ = [
    # Base classes
    "BaseKafkaProducer",
    "BaseKafkaConsumer",
    
    # Producers
    "DocumentProducer",
    "RAGProducer", 
    "ExtractionProducer",
    "QueryProducer",
    
    # Consumers
    "DocumentConsumer",
    "create_simple_document_consumer",
    
    # Event bus
    "EventBus",
    "EventType",
    "create_event_bus",
    "get_all_event_types"
]