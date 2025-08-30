"""
Base Kafka consumer with common functionality abstracted.
All specific consumers inherit from this class to minimize code duplication.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Optional
from threading import Thread, Event

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from ..config.settings import get_settings
from ..interfaces.messaging import IEventConsumer


class BaseKafkaConsumer(IEventConsumer, ABC):
    """
    Abstract base class for Kafka consumers.
    Handles common Kafka connection and consumption logic.
    """
    
    def __init__(self, group_id: Optional[str] = None):
        """
        Initialize Kafka consumer with settings from configuration.
        
        Args:
            group_id: Consumer group ID. If None, uses class name.
        """
        self.settings = get_settings()
        self.group_id = group_id or self.__class__.__name__.lower()
        self.logger = self._setup_logging()
        self._consumer = None
        self._stop_event = Event()
        self._consumer_thread = None
        self._connect()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the consumer."""
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
            self._consumer = KafkaConsumer(
                *self.get_subscribed_topics(),
                bootstrap_servers=self.settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='earliest',
                enable_auto_commit=False,  # Manual commit for better control
                max_poll_records=10  # Process in small batches
            )
            self.logger.info(
                f"Connected to Kafka as group '{self.group_id}' "
                f"for topics: {self.get_subscribed_topics()}"
            )
        except Exception as e:
            self.logger.error(f"Failed to connect to Kafka: {e}")
            raise ConnectionError(f"Kafka connection failed: {e}")
    
    def consume_events(self) -> List[Dict[str, Any]]:
        """
        Consume events from subscribed topics.
        
        Returns:
            List[Dict[str, Any]]: List of consumed messages
        """
        messages = []
        try:
            # Poll for messages with timeout
            message_batch = self._consumer.poll(timeout_ms=1000, max_records=10)
            
            for topic_partition, records in message_batch.items():
                for record in records:
                    message_data = {
                        'topic': record.topic,
                        'partition': record.partition,
                        'offset': record.offset,
                        'key': record.key,
                        'value': record.value,
                        'timestamp': record.timestamp
                    }
                    messages.append(message_data)
                    
                    # Process message
                    try:
                        self.process_message(record.value, record.topic, record.key)
                    except Exception as e:
                        self.logger.error(f"Error processing message: {e}")
                        # Continue processing other messages
            
            # Commit offsets after successful processing
            if messages:
                self._consumer.commit()
                self.logger.info(f"Processed and committed {len(messages)} messages")
                
        except KafkaError as e:
            self.logger.error(f"Kafka error during consumption: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during consumption: {e}")
            
        return messages
    
    def subscribe_to_topic(self, topic: str) -> bool:
        """
        Subscribe to an additional topic.
        
        Args:
            topic: Topic name to subscribe to
            
        Returns:
            bool: True if subscription successful
        """
        try:
            current_topics = list(self.get_subscribed_topics())
            if topic not in current_topics:
                current_topics.append(topic)
                self._consumer.subscribe(current_topics)
                self.logger.info(f"Subscribed to additional topic: {topic}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to subscribe to topic {topic}: {e}")
            return False
    
    def start_consuming(self) -> None:
        """Start consuming messages in a background thread."""
        if self._consumer_thread and self._consumer_thread.is_alive():
            self.logger.warning("Consumer already running")
            return
            
        self._stop_event.clear()
        self._consumer_thread = Thread(target=self._consume_loop, daemon=True)
        self._consumer_thread.start()
        self.logger.info("Started background message consumption")
    
    def stop_consuming(self) -> None:
        """Stop consuming messages and wait for thread to finish."""
        if self._consumer_thread and self._consumer_thread.is_alive():
            self._stop_event.set()
            self._consumer_thread.join(timeout=10)
            self.logger.info("Stopped background message consumption")
    
    def _consume_loop(self) -> None:
        """Background consumption loop."""
        while not self._stop_event.is_set():
            self.consume_events()
    
    @abstractmethod
    def get_subscribed_topics(self) -> List[str]:
        """Get list of topics this consumer subscribes to. Must be implemented by subclasses."""
        pass
    
    @abstractmethod  
    def process_message(self, message_data: Dict[str, Any], topic: str, key: Optional[str] = None) -> bool:
        """
        Process a consumed message. Must be implemented by subclasses.
        
        Args:
            message_data: Deserialized message data
            topic: Topic the message came from
            key: Optional message key
            
        Returns:
            bool: True if processing successful
        """
        pass
    
    def close(self) -> None:
        """Close Kafka consumer connection."""
        self.stop_consuming()
        if self._consumer:
            self._consumer.close()
            self.logger.info("Kafka consumer connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# HELPER FUNCTIONS

def extract_message_metadata(record) -> Dict[str, Any]:
    """
    Extract metadata from Kafka record.
    
    Args:
        record: Kafka consumer record
        
    Returns:
        Dict containing message metadata
    """
    return {
        'topic': record.topic,
        'partition': record.partition,
        'offset': record.offset,
        'timestamp': record.timestamp,
        'key': record.key
    }


def is_message_duplicate(message_key: str, processed_keys: set) -> bool:
    """
    Check if message has already been processed (simple deduplication).
    
    Args:
        message_key: Message key to check
        processed_keys: Set of already processed keys
        
    Returns:
        bool: True if message is duplicate
    """
    return message_key in processed_keys if message_key else False