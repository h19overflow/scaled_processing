"""
Kafka topic setup script for the document processing system.
Creates all required topics with appropriate configurations.
"""

import time
import logging
from kafka import KafkaAdminClient
from kafka.admin import ConfigResource, ConfigResourceType, NewTopic
from kafka.errors import TopicAlreadyExistsError, KafkaError

from .event_bus import EventType
from src.backend.doc_processing_system.config.settings import get_settings


class KafkaTopicManager:
    """Manages Kafka topic creation and configuration."""
    
    def __init__(self):
        """Initialize Kafka admin client."""
        self.settings = get_settings()
        self.logger = self._setup_logging()
        self.admin_client = None
        self._connect_with_retry()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for topic manager."""
        logger = logging.getLogger("KafkaTopicManager")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _connect_with_retry(self, max_retries: int = 30, retry_delay: int = 2) -> None:
        """Connect to Kafka with retry logic for startup."""
        for attempt in range(max_retries):
            try:
                self.admin_client = KafkaAdminClient(
                    bootstrap_servers=self.settings.KAFKA_BOOTSTRAP_SERVERS,
                    client_id="topic_setup_client"
                )
                
                # Test connection by listing topics
                self.admin_client.list_topics()
                self.logger.info(f"Connected to Kafka: {self.settings.KAFKA_BOOTSTRAP_SERVERS}")
                return
                
            except Exception as e:
                self.logger.warning(
                    f"Connection attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise ConnectionError(f"Failed to connect to Kafka after {max_retries} attempts")
    
    def get_topic_configurations(self) -> dict:
        """
        Get topic configurations for all system topics.
        
        Returns:
            dict: Topic name -> configuration mapping
        """
        # Base configuration for all topics
        base_config = {
            'cleanup.policy': 'delete',
            'retention.ms': '604800000',  # 7 days
            'segment.ms': '86400000',     # 1 day
            'compression.type': 'snappy'
        }
        
        # Topic-specific configurations
        topic_configs = {
            # File system monitoring (low-medium throughput)
            EventType.FILE_DETECTED.value: {
                **base_config,
                'partitions': 3,
                'replication_factor': 1
            },
            
            # Document lifecycle topics (high throughput)
            EventType.DOCUMENT_AVAILABLE.value: {
                **base_config,
                'partitions': 6,
                'replication_factor': 1,
                'min.insync.replicas': '1'
            },
            EventType.WORKFLOW_INITIALIZED.value: {
                **base_config,
                'partitions': 3,
                'replication_factor': 1
            },
            
            # RAG workflow topics (medium throughput)
            EventType.CHUNKING_COMPLETE.value: {
                **base_config,
                'partitions': 4,
                'replication_factor': 1
            },
            EventType.EMBEDDING_READY.value: {
                **base_config,
                'partitions': 4,
                'replication_factor': 1
            },
            EventType.INGESTION_COMPLETE.value: {
                **base_config,
                'partitions': 3,
                'replication_factor': 1
            },
            
            # Extraction workflow topics (high throughput for tasks)
            EventType.FIELD_INIT_COMPLETE.value: {
                **base_config,
                'partitions': 2,
                'replication_factor': 1
            },
            EventType.AGENT_SCALING_COMPLETE.value: {
                **base_config,
                'partitions': 2,
                'replication_factor': 1
            },
            EventType.EXTRACTION_TASKS.value: {
                **base_config,
                'partitions': 8,  # High throughput for parallel agents
                'replication_factor': 1
            },
            EventType.EXTRACTION_COMPLETE.value: {
                **base_config,
                'partitions': 3,
                'replication_factor': 1
            },
            
            # Query processing topics (medium throughput)
            EventType.QUERY_RECEIVED.value: {
                **base_config,
                'partitions': 4,
                'replication_factor': 1
            },
            EventType.RAG_QUERY_COMPLETE.value: {
                **base_config,
                'partitions': 3,
                'replication_factor': 1
            },
            EventType.STRUCTURED_QUERY_COMPLETE.value: {
                **base_config,
                'partitions': 3,
                'replication_factor': 1
            },
            EventType.HYBRID_QUERY_COMPLETE.value: {
                **base_config,
                'partitions': 3,
                'replication_factor': 1
            }
        }
        
        return topic_configs
    
    def create_all_topics(self) -> bool:
        """
        Create all system topics with their configurations.
        
        Returns:
            bool: True if all topics created successfully
        """
        topic_configs = self.get_topic_configurations()
        topics_to_create = []
        
        for topic_name, config in topic_configs.items():
            # Make a copy to avoid modifying the original
            config_copy = config.copy()
            
            # Extract partition and replication info
            partitions = config_copy.pop('partitions')
            replication_factor = config_copy.pop('replication_factor')
            
            # Create NewTopic object
            new_topic = NewTopic(
                name=topic_name,
                num_partitions=partitions,
                replication_factor=replication_factor,
                topic_configs=config_copy
            )
            topics_to_create.append(new_topic)
        
        try:
            # Create topics
            future_map = self.admin_client.create_topics(
                new_topics=topics_to_create,
                validate_only=False,
                timeout_ms=30000
            )
            
            # Check results
            created_topics = []
            failed_topics = []
            
            # Handle different response formats based on kafka-python version
            if hasattr(future_map, 'items'):
                # Standard dict-like response
                items = future_map.items()
            else:
                # Response object - extract topic futures differently
                items = [(topic.name, future_map[topic.name]) for topic in topics_to_create]
            
            for topic_name, future in items:
                try:
                    future.result()  # Wait for completion
                    created_topics.append(topic_name)
                    self.logger.info(f"✅ Created topic: {topic_name}")
                except TopicAlreadyExistsError:
                    self.logger.info(f"ℹ️  Topic already exists: {topic_name}")
                    created_topics.append(topic_name)
                except Exception as e:
                    self.logger.error(f"❌ Failed to create topic {topic_name}: {e}")
                    failed_topics.append(topic_name)
            
            if failed_topics:
                self.logger.error(f"Failed to create {len(failed_topics)} topics: {failed_topics}")
                return False
            
            self.logger.info(f"✅ All {len(created_topics)} topics ready")
            return True
            
        except TopicAlreadyExistsError:
            # This shouldn't happen since we handle individual topics above,
            # but just in case all topics already exist
            self.logger.info("ℹ️  All topics already exist")
            return True
        except Exception as e:
            self.logger.error(f"Unexpected error during topic creation: {e}")
            return False
    
    def list_topics(self) -> dict:
        """
        List all topics and their configurations.
        
        Returns:
            dict: Topic information
        """
        try:
            topic_names = self.admin_client.list_topics()
            
            # Get detailed information for system topics only
            system_topics = [name for name in topic_names 
                           if any(event.value == name for event in EventType)]
            
            if not system_topics:
                return {}
            
            # Describe topics to get partition counts
            topic_descriptions = self.admin_client.describe_topics(system_topics)
            
            topic_info = {}
            for topic_desc in topic_descriptions:
                try:
                    topic_name = topic_desc['topic']
                    partitions = topic_desc.get('partitions', [])
                    
                    topic_info[topic_name] = {
                        'partitions': len(partitions),
                        'exists': True,
                        'partition_info': [
                            {
                                'partition': p['partition'],
                                'leader': p['leader'],
                                'replicas': len(p.get('replicas', []))
                            }
                            for p in partitions
                        ]
                    }
                except Exception as e:
                    # If describe fails, at least show it exists
                    if 'topic_name' in locals():
                        topic_info[topic_name] = {
                            'partitions': 'describe_failed',
                            'exists': True,
                            'error': str(e)
                        }
            
            return topic_info
            
        except Exception as e:
            self.logger.error(f"Failed to list topics: {e}")
            return {}
    
    def verify_all_topics(self) -> bool:
        """
        Verify all required topics exist.
        
        Returns:
            bool: True if all topics exist
        """
        try:
            existing_topics = set(self.admin_client.list_topics())
            required_topics = set(event.value for event in EventType)
            
            missing_topics = required_topics - existing_topics
            
            if missing_topics:
                self.logger.error(f"Missing topics: {missing_topics}")
                return False
            
            self.logger.info("✅ All required topics exist")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to verify topics: {e}")
            return False
    
    def close(self) -> None:
        """Close admin client connection."""
        if self.admin_client:
            self.admin_client.close()
            self.logger.info("Kafka admin client closed")


def main():
    """Main function to set up all Kafka topics."""
    print("🚀 Setting up Kafka topics for document processing system...")
    
    try:
        # Create topic manager
        topic_manager = KafkaTopicManager()
        
        # Create all topics
        success = topic_manager.create_all_topics()
        
        if success:
            # Verify topics
            topic_manager.verify_all_topics()
            
            # List all topics for verification
            topic_info = topic_manager.list_topics()
            
            print(f"\n📊 Topic Summary:")
            for topic, info in topic_info.items():
                if any(event.value == topic for event in EventType):
                    print(f"  • {topic}: {info['partitions']} partitions")
            
            print("\n✅ Kafka topics setup completed successfully!")
        else:
            print("\n❌ Topic setup failed!")
            return 1
        
        # Close connection
        topic_manager.close()
        return 0
        
    except Exception as e:
        print(f"\n💥 Setup failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())