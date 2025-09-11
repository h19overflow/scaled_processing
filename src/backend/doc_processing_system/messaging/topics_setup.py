from confluent_kafka.admin import AdminClient, NewTopic
import logging
from typing import Dict, Any

def create_topics(topic_configs: Dict[str, Any], broker: str = 'localhost:9092') -> bool:
    """Create Kafka topics from configuration."""
    logger = logging.getLogger(__name__)
    
    if not topic_configs:
        logger.warning("No topics to create")
        return True
        
    try:
        admin_client = AdminClient({'bootstrap.servers': broker})
        topic_list = []
        
        for topic_name, config in topic_configs.items():
            num_partitions = config.get('num_partitions', 1)
            replication_factor = config.get('replication_factor', 1)
            topic_config = config.get('config', {})
            topic_list.append(NewTopic(topic_name, num_partitions, replication_factor, config=topic_config))

        fs = admin_client.create_topics(topic_list)
        success = True
        
        for topic, f in fs.items():
            try:
                f.result()
                logger.info(f"Topic '{topic}' created or already exists")
            except Exception as e:
                logger.error(f"Failed to create topic '{topic}': {e}")
                success = False
                
        return success
        
    except Exception as e:
        logger.error(f"Failed to create topics: {e}")
        return False


if __name__ == "__main__":
    topics = {


        "document_pipeline_completed": {
            "num_partitions": 6,
            "replication_factor": 1,
            "config": {
                "cleanup.policy": "compact",
                "compression.type": "lz4",
                "retention.ms": "604800000"  # 7 days
            }

        }
        ,
        "rag_pipeline_completed": {
            "num_partitions": 6,
            "replication_factor": 1,
            "config": {
                "cleanup.policy": "compact",
                "compression.type": "lz4",
                "retention.ms": "604800000"
            }
        }
        ,
        "structured_extraction_completed": {
            "num_partitions": 6,
            "replication_factor": 1,
            "config": {
                "cleanup.policy": "compact",
                "compression.type": "lz4",
                "retention.ms": "604800000"
            }
        }
    ,
        "file_detected": {
            "num_partitions": 6,
            "replication_factor": 1,
            "config": {
                "cleanup.policy": "compact",
                "compression.type": "lz4",
                "retention.ms": "604800000"
            }
        }
    }

    create_topics(topics)

