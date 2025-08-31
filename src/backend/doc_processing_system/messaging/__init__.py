"""
Event-driven messaging system organized by processing stages.

This package contains all Kafka producers and consumers organized by the
document processing pipeline stages for clear data flow and maintainability.

Structure:
- base/: Base classes for producers and consumers
- file_ingestion/: File detection and initial processing
- document_processing/: Document workflow coordination  
- rag_pipeline/: RAG processing events
- extraction_pipeline/: Structured extraction events
- query_processing/: Query handling events
- orchestration/: Event routing and system management
"""

# Import key components for easy access
from .base import BaseKafkaConsumer, BaseKafkaProducer
from .file_ingestion import FileProcessingConsumer
from .document_processing import DocumentProducer, DocumentConsumer
from .rag_pipeline import RAGProducer
from .extraction_pipeline import ExtractionProducer
from .query_processing import QueryProducer
from .orchestration import EventBus, EventType, KafkaTopicManager

__all__ = [
    # Base classes
    "BaseKafkaConsumer",
    "BaseKafkaProducer",
    
    # File ingestion
    "FileProcessingConsumer",
    
    # Document processing
    "DocumentProducer",
    "DocumentConsumer",
    
    # Pipeline producers
    "RAGProducer",
    "ExtractionProducer", 
    "QueryProducer",
    
    # Orchestration
    "EventBus",
    "EventType",
    "KafkaTopicManager"
]