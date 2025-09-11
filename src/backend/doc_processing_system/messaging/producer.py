from confluent_kafka import Producer
import json
import logging
import time
from typing import Dict, Any, Optional

class ProducerHandler:
    def __init__(self, broker: str, config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(__name__)
        
        # Build producer config
        producer_config = {'bootstrap.servers': broker}
        if config:
            producer_config.update(config)
            
        # Validate broker connection
        if not broker:
            raise ValueError("Broker address is required")
            
        try:
            self.producer = Producer(producer_config)
            self.logger.info(f"Producer initialized with broker: {broker}")
        except Exception as e:
            self.logger.error(f"Failed to initialize producer: {e}")
            raise

    def produce_message(self, topic: str, key: str, value: Any, retries: int = 3) -> bool | None:
        if isinstance(value, dict):
            value = json.dumps(value)
            
        self.logger.info(f"Producing to topic={topic}, key={key}")
        
        for attempt in range(retries + 1):
            try:
                self.producer.produce(
                    topic, 
                    key=key, 
                    value=value, 
                    callback=lambda err, msg: self._delivery_report(err, msg)
                )
                self.producer.flush(timeout=10)
                return True
                
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.error(f"All {retries + 1} attempts failed for message to {topic}")
                    return False

    def close(self):
        """Gracefully close the producer connection."""
        if hasattr(self, 'producer'):
            try:
                self.producer.flush(timeout=30)
                self.logger.info("Producer closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing producer: {e}")

    def _delivery_report(self, err, msg):
        if err is not None:
            self.logger.error(f"Delivery failed for record {msg.key()}: {err}")
        else:
            self.logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
