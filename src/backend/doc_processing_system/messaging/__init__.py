"""
Messaging package for Kafka producers and consumers.
Provides event-driven communication between system components.
"""

# Base classes
from .producers_n_consumers.base_producer import BaseKafkaProducer
from .producers_n_consumers.base_consumer import BaseKafkaConsumer

# Specific producers
from .producers_n_consumers.document_producer import DocumentProducer
from .producers_n_consumers.rag_producer import RAGProducer
from .producers_n_consumers.extraction_producer import ExtractionProducer
from .producers_n_consumers.query_producer import QueryProducer

# Specific consumers  
from .producers_n_consumers.document_consumer import DocumentConsumer, create_simple_document_consumer

# Event bus
from .producers_n_consumers.event_bus import EventBus, EventType, create_event_bus, get_all_event_types

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