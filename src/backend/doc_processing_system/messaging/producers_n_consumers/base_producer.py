"""
Base Kafka producer with common functionality abstracted.
All specific producers inherit from this class to minimize code duplication.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from kafka import KafkaProducer
from kafka.errors import KafkaError

from ...config.settings import get_settings
from ...interfaces.messaging import IEventPublisher


class BaseKafkaProducer(IEventPublisher, ABC):
    """
    Abstract base class for Kafka producers.
    Handles common Kafka connection and publishing logic.
    """
    
    def __init__(self):
        """Initialize Kafka producer with settings from configuration."""
        self.settings = get_settings()
        self.logger = self._setup_logging()
        self._producer = None
        self._connect()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the producer."""
        logger = logging.getLogger(f"{self.__class__.__name__}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _connect(self) -> None:
        """Establish connection to Kafka cluster."""
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=self.settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                retries=3,
                acks='all',
                enable_idempotence=True
            )
            self.logger.info(f"Connected to Kafka: {self.settings.KAFKA_BOOTSTRAP_SERVERS}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Kafka: {e}")
            raise ConnectionError(f"Kafka connection failed: {e}")
    
    def publish_event(self, topic: str, event_data: Dict[str, Any], key: Optional[str] = None) -> bool:
        """
        Publish an event to specified Kafka topic.
        
        Args:
            topic: Kafka topic name
            event_data: Event data to publish
            key: Optional message key for partitioning
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            # Add timestamp if not present
            if 'timestamp' not in event_data:
                event_data['timestamp'] = datetime.now().isoformat()
            
            # Send message
            future = self._producer.send(topic, value=event_data, key=key)
            
            # Wait for confirmation (synchronous send)
            record_metadata = future.get(timeout=10)
            
            self.logger.info(
                f"Published to {topic}:{record_metadata.partition}:{record_metadata.offset}"
            )
            return True
            
        except KafkaError as e:
            self.logger.error(f"Kafka error publishing to {topic}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error publishing to {topic}: {e}")
            return False
    
    def publish(self, event_data: Dict[str, Any]) -> bool:
        """
        Generic publish method - delegates to specific topic logic.
        Subclasses should override this with topic-specific logic.
        """
        return self.publish_event(self.get_default_topic(), event_data)
    
    @abstractmethod
    def get_default_topic(self) -> str:
        """Get the default topic for this producer. Must be implemented by subclasses."""
        pass
    
    def close(self) -> None:
        """Close Kafka producer connection."""
        if self._producer:
            self._producer.close()
            self.logger.info("Kafka producer connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# HELPER FUNCTIONS

def create_message_key(document_id: str, user_id: Optional[str] = None) -> str:
    """
    Create a consistent message key for partitioning.
    
    Args:
        document_id: Document identifier
        user_id: Optional user identifier
        
    Returns:
        str: Message key for Kafka partitioning
    """
    if user_id:
        return f"{user_id}:{document_id}"
    return document_id


def validate_event_data(event_data: Dict[str, Any], required_fields: list) -> bool:
    """
    Validate that event data contains required fields.
    
    Args:
        event_data: Event data dictionary
        required_fields: List of required field names
        
    Returns:
        bool: True if all required fields present
    """
    return all(field in event_data for field in required_fields)