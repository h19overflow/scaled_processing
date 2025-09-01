"""
Central event bus for routing messages between producers and consumers.
Provides unified interface for event publishing and subscription management.
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from threading import Thread, Event as ThreadEvent
from enum import Enum

from ..document_processing.document_producer import DocumentProducer
from ..document_processing.document_consumer import DocumentConsumer
from ..rag_pipeline.rag_producer import RAGProducer
from ..extraction_pipeline.extraction_producer import ExtractionProducer
from ..query_processing.query_producer import QueryProducer


class EventType(str, Enum):
    """Types of events in the system."""
    FILE_DETECTED = "file-detected"
    DOCUMENT_AVAILABLE = "document-available"
    WORKFLOW_INITIALIZED = "workflow-initialized"
    CHUNKING_COMPLETE = "chunking-complete"
    EMBEDDING_READY = "embedding-ready"
    INGESTION_COMPLETE = "ingestion-complete"
    FIELD_INIT_COMPLETE = "field-init-complete"
    AGENT_SCALING_COMPLETE = "agent-scaling-complete"
    EXTRACTION_TASKS = "extraction-tasks"
    EXTRACTION_COMPLETE = "extraction-complete"
    QUERY_RECEIVED = "query-received"
    RAG_QUERY_COMPLETE = "rag-query-complete"
    STRUCTURED_QUERY_COMPLETE = "structured-query-complete"
    HYBRID_QUERY_COMPLETE = "hybrid-query-complete"


class EventBus:
    """
    Central event bus for coordinating all Kafka producers and consumers.
    Provides unified interface for publishing and consuming events.
    """
    
    def __init__(self):
        """Initialize event bus with all producers."""
        self.logger = self._setup_logging()
        self._producers = self._initialize_producers()
        self._consumers = {}
        self._topic_router = self._create_topic_router()
        self._running_consumers = []
        
        self.logger.info("Event bus initialized with all producers")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the event bus."""
        logger = logging.getLogger("EventBus")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_producers(self) -> Dict[str, Any]:
        """Initialize all producer instances."""
        return {
            "document": DocumentProducer(),
            "rag": RAGProducer(),
            "extraction": ExtractionProducer(),
            "query": QueryProducer()
        }
    
    def _create_topic_router(self) -> Dict[str, str]:
        """Create mapping of event types to producer types."""
        return {
            EventType.FILE_DETECTED: "document",
            EventType.DOCUMENT_AVAILABLE: "document",
            EventType.WORKFLOW_INITIALIZED: "document",
            EventType.CHUNKING_COMPLETE: "rag",
            EventType.EMBEDDING_READY: "rag", 
            EventType.INGESTION_COMPLETE: "rag",
            EventType.FIELD_INIT_COMPLETE: "extraction",
            EventType.AGENT_SCALING_COMPLETE: "extraction",
            EventType.EXTRACTION_TASKS: "extraction",
            EventType.EXTRACTION_COMPLETE: "extraction",
            EventType.QUERY_RECEIVED: "query",
            EventType.RAG_QUERY_COMPLETE: "query",
            EventType.STRUCTURED_QUERY_COMPLETE: "query",
            EventType.HYBRID_QUERY_COMPLETE: "query"
        }
    
    def publish(self, event_type: EventType, event_data: Dict[str, Any], key: Optional[str] = None) -> bool:
        """
        Publish event through appropriate producer.
        
        Args:
            event_type: Type of event to publish
            event_data: Event data dictionary
            key: Optional message key
            
        Returns:
            bool: True if published successfully
        """
        try:
            # Route to appropriate producer
            producer_type = self._topic_router.get(event_type)
            if not producer_type:
                self.logger.error(f"No producer found for event type: {event_type}")
                return False
            
            producer = self._producers.get(producer_type)
            if not producer:
                self.logger.error(f"Producer {producer_type} not available")
                return False
            
            # Publish through specific producer
            success = producer.publish_event(
                topic=event_type.value,
                event_data=event_data,
                key=key
            )
            
            if success:
                self.logger.info(f"Event published: {event_type} via {producer_type} producer")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to publish event {event_type}: {e}")
            return False
    
    def subscribe(self, event_types: List[EventType], consumer_group: str = "default") -> str:
        """
        Create and start consumer for specified event types.
        
        Args:
            event_types: List of event types to subscribe to
            consumer_group: Consumer group name
            
        Returns:
            str: Consumer ID for managing the subscription
        """
        try:
            # Create consumer ID
            consumer_id = f"{consumer_group}_{len(self._consumers)}"
            
            # Create document consumer for now (supports all current event types)
            consumer = DocumentConsumer(consumer_group)
            
            # Store consumer reference
            self._consumers[consumer_id] = {
                "consumer": consumer,
                "event_types": event_types,
                "group": consumer_group
            }
            
            # Start consuming in background
            consumer.start_consuming()
            self._running_consumers.append(consumer_id)
            
            self.logger.info(
                f"Subscribed to events {[et.value for et in event_types]} "
                f"with consumer {consumer_id}"
            )
            
            return consumer_id
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to events: {e}")
            return ""
    
    def unsubscribe(self, consumer_id: str) -> bool:
        """
        Stop and remove consumer.
        
        Args:
            consumer_id: Consumer ID to remove
            
        Returns:
            bool: True if unsubscribed successfully
        """
        try:
            if consumer_id not in self._consumers:
                self.logger.warning(f"Consumer {consumer_id} not found")
                return False
            
            # Stop consumer
            consumer_info = self._consumers[consumer_id]
            consumer_info["consumer"].stop_consuming()
            
            # Remove from tracking
            del self._consumers[consumer_id]
            if consumer_id in self._running_consumers:
                self._running_consumers.remove(consumer_id)
            
            self.logger.info(f"Unsubscribed consumer {consumer_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe consumer {consumer_id}: {e}")
            return False
    
    def get_topics(self) -> List[str]:
        """
        Get list of all available topics.
        
        Returns:
            List[str]: Available topic names
        """
        return [event_type.value for event_type in EventType]
    
    def get_producer_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all producers.
        
        Returns:
            Dict with producer statistics
        """
        stats = {}
        for producer_name, producer in self._producers.items():
            stats[producer_name] = {
                "class": producer.__class__.__name__,
                "topics": [event_type.value for event_type, prod_type in self._topic_router.items() 
                          if prod_type == producer_name]
            }
        return stats
    
    def get_consumer_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all consumers.
        
        Returns:
            Dict with consumer statistics
        """
        stats = {}
        for consumer_id, consumer_info in self._consumers.items():
            stats[consumer_id] = {
                "group": consumer_info["group"],
                "event_types": [et.value for et in consumer_info["event_types"]],
                "running": consumer_id in self._running_consumers
            }
        return stats
    
    def close_all(self) -> None:
        """Close all producers and consumers."""
        # Stop all consumers
        for consumer_id in list(self._consumers.keys()):
            self.unsubscribe(consumer_id)
        
        # Close all producers
        for producer_name, producer in self._producers.items():
            try:
                producer.close()
                self.logger.info(f"Closed {producer_name} producer")
            except Exception as e:
                self.logger.error(f"Error closing {producer_name} producer: {e}")
        
        self.logger.info("Event bus closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_all()


# HELPER FUNCTIONS

def create_event_bus() -> EventBus:
    """
    Create and return configured event bus instance.
    
    Returns:
        EventBus: Configured event bus
    """
    return EventBus()


def get_all_event_types() -> List[EventType]:
    """
    Get list of all available event types.
    
    Returns:
        List[EventType]: All event types in the system
    """
    return list(EventType)