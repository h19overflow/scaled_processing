from confluent_kafka import Consumer




class ConsumerHandler:
    def __init__(self, broker, group_id, topics):
        self.consumer = Consumer({
            'bootstrap.servers': broker,
            'group.id': group_id,
            'auto.offset.reset': 'earliest'
        })
        self.topics = topics
        self.consumer.subscribe(self.topics)

    def consume_messages(self, timeout=1.0):
        messages = []
        while True:
            msg = self.consumer.poll(timeout)
            if msg is None:
                break
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue
            messages.append(msg.value().decode('utf-8'))
        return messages

    def close(self):
        self.consumer.close()