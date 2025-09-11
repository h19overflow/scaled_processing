from confluent_kafka.admin import AdminClient, NewTopic


def create_topics(topic_configs: dict):
    admin_client = AdminClient({'bootstrap.servers': 'localhost:9092'})
    topic_list = []
    for topic_name, config in topic_configs.items():
        num_partitions = config.get('num_partitions', 1)
        replication_factor = config.get('replication_factor', 1)
        topic_config = config.get('config', {})
        topic_list.append(NewTopic(topic_name, num_partitions, replication_factor, config=topic_config))

    # --- Wait for futures:
    fs = admin_client.create_topics(topic_list)
    for topic, f in fs.items():
        try:
            f.result()  # The result itself is None
            print(f"Topic {topic} created or already exists")
        except Exception as e:
            print(f"Failed to create topic {topic}: {e}")


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

    }
    create_topics(topics)

