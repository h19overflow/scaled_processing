from confluent_kafka import Consumer, KafkaError
import logging
import signal
from typing import List, Dict, Any, Optional, Callable

class ConsumerHandler:
    def __init__(self, broker: str, group_id: str, topics: List[str], config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(__name__)
        self.running = False
        
        # Validate inputs
        if not broker:
            raise ValueError("Broker address is required")
        if not group_id:
            raise ValueError("Group ID is required")
        if not topics:
            raise ValueError("Topics list cannot be empty")
            
        # Build consumer config
        consumer_config = {
            'bootstrap.servers': broker,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            'session.timeout.ms': 30000,
            'heartbeat.interval.ms': 10000
        }
        if config:
            consumer_config.update(config)
            
        try:
            self.consumer = Consumer(consumer_config)
            self.topics = topics
            self.consumer.subscribe(self.topics)
            self.logger.info(f"Consumer initialized for group '{group_id}' on topics: {topics}")
        except Exception as e:
            self.logger.error(f"Failed to initialize consumer: {e}")
            raise
            
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def consume_messages(self, message_handler: Callable[[str, str, str], None], timeout: float = 1.0):
        """Consume messages and process them with the provided handler."""
        self.running = True
        self.logger.info("Starting messag e consumption...")
        
        try:
            while self.running:
                msg = self.consumer.poll(timeout)
                
                if msg is None:
                    continue
                    
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        self.logger.debug(f"Reached end of partition {msg.partition()}")
                    else:
                        self.logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                try:
                    # Decode message
                    key = msg.key().decode('utf-8') if msg.key() else None
                    value = msg.value().decode('utf-8')
                    topic = msg.topic()
                    
                    self.logger.debug(f"Processing message from {topic}: key={key}")
                    
                    # Process message with handler
                    message_handler(topic, key, value)
                    
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    # Continue processing other messages
                    
        except Exception as e:
            self.logger.error(f"Critical error in consumer loop: {e}")
            raise
        finally:
            self.close()

    def close(self):
        """Gracefully close the consumer connection."""
        self.running = False
        if hasattr(self, 'consumer'):
            try:
                self.consumer.close()
                self.logger.info("Consumer closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing consumer: {e}")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False