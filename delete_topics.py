from confluent_kafka.admin import AdminClient, NewTopic


def recreate_topics_to_clear_data(bootstrap_servers='localhost:9092'):
    admin_client = AdminClient({'bootstrap.servers': bootstrap_servers})

    # List of topics that failed deletion
    failed_topics = [
        'file_detected',
        'structured_extraction_completed',
        'rag_pipeline_completed',
        'document_pipeline_completed'
    ]

    # Get current topic configurations
    topic_configs = {}
    for topic_name in failed_topics:
        metadata = admin_client.list_topics(topic_name, timeout=10)
        if topic_name in metadata.topics:
            topic_metadata = metadata.topics[topic_name]
            num_partitions = len(topic_metadata.partitions)
            topic_configs[topic_name] = num_partitions

    print(f"Deleting {len(failed_topics)} topics...")

    # Delete topics
    delete_result = admin_client.delete_topics(failed_topics, operation_timeout=30.0)
    for topic, future in delete_result.items():
        try:
            future.result()
            print(f"✓ Deleted topic: {topic}")
        except Exception as e:
            print(f"✗ Failed to delete topic {topic}: {e}")
            return

    # Wait a moment for deletion to complete
    import time
    time.sleep(5)

    # Recreate topics with same partition count
    new_topics = []
    for topic_name, partition_count in topic_configs.items():
        new_topics.append(NewTopic(
            topic=topic_name,
            num_partitions=partition_count,
            replication_factor=1  # Adjust as needed
        ))

    print(f"Recreating {len(new_topics)} topics...")
    create_result = admin_client.create_topics(new_topics)
    for topic, future in create_result.items():
        try:
            future.result()
            print(f"✓ Recreated topic: {topic}")
        except Exception as e:
            print(f"✗ Failed to recreate topic {topic}: {e}")


# Execute the function
recreate_topics_to_clear_data('localhost:9092')
