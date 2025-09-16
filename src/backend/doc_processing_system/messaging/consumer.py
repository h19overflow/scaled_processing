import logging
import threading
from abc import ABC, abstractmethod
from confluent_kafka import Consumer, KafkaError
from typing import List, Dict, Any, Optional

class ConsumerHandler(ABC):
    """Abstract base class for Kafka consumers with multi-threading support."""
    
    def __init__(self, broker: str, topics: List[str], group_id: str, num_consumers: int = 1, config: Optional[Dict[str, Any]] = None):
        # Validate inputs
        if not broker:
            raise ValueError("Broker address is required")
        if not group_id:
            raise ValueError("Group ID is required")
        if not topics:
            raise ValueError("Topics list cannot be empty")
        if num_consumers < 1 or num_consumers > 6:
            raise ValueError("num_consumers must be between 1 and 6")
            
        self.broker = broker
        self.topics = topics
        self.group_id = group_id
        self.num_consumers = num_consumers
        self.logger = logging.getLogger(__name__)
        self.consumer_threads = []
        self.running = False
        
        # Build consumer config
        self.consumer_config = {
            'bootstrap.servers': broker,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            'session.timeout.ms': 30000,
            'heartbeat.interval.ms': 10000
        }
        if config:
            self.consumer_config.update(config)
            
        self.logger.info(f"Consumer initialized for group '{group_id}' on topics: {topics} with {num_consumers} consumers")

    @abstractmethod
    def handle_message(self, topic: str, key: str, value: str) -> None:
        """Handle a single Kafka message. Subclasses must implement this method."""
        pass
    
    def _handle_message_wrapper(self, topic: str, key: str, value: str) -> None:
        """Wrapper that adds error handling around handle_message."""
        try:
            self.handle_message(topic, key, value)
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    def _start_single_consumer(self, consumer_id: int) -> None:
        """Start a single consumer in its own thread."""
        try:
            consumer = Consumer(self.consumer_config)
            consumer.subscribe(self.topics)
            
            self.logger.info(f"Starting consumer {consumer_id}/{self.num_consumers}...")
            
            # Manual consume loop without signal handlers
            try:
                while self.running:
                    msg = consumer.poll(1.0)
                    
                    if msg is None:
                        continue
                        
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            continue
                        else:
                            self.logger.error(f"Consumer {consumer_id} error: {msg.error()}")
                        continue
                    
                    # Process message
                    key = msg.key().decode('utf-8') if msg.key() else None
                    value = msg.value().decode('utf-8')
                    topic = msg.topic()
                    
                    self._handle_message_wrapper(topic, key, value)
                    
            except KeyboardInterrupt:
                self.logger.info(f"Consumer {consumer_id} shutting down...")
            finally:
                consumer.close()
                
        except Exception as e:
            self.logger.error(f"Consumer {consumer_id} failed: {e}")
    
    def start(self) -> None:
        """Start multiple consumers in separate threads."""
        self.running = True
        self.logger.info(f"Starting {self.num_consumers} consumers...")
        
        # Start each consumer in its own thread
        for i in range(self.num_consumers):
            consumer_thread = threading.Thread(
                target=self._start_single_consumer,
                args=(i + 1,),
                daemon=True,
                name=f"consumer-{i + 1}"
            )
            consumer_thread.start()
            self.consumer_threads.append(consumer_thread)
        
        # Wait for all consumer threads
        try:
            for thread in self.consumer_threads:
                thread.join()
        except KeyboardInterrupt:
            self.logger.info("Shutting down consumers...")
    
    def stop(self) -> None:
        """Stop all consumers gracefully."""
        self.logger.info("Stopping all consumers...")
        self.running = False
        # Consumer threads will stop when main thread exits due to daemon=True