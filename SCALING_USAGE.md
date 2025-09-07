# Consumer Scaling Usage

Simple consumer scaling is now built directly into the DocumentProcessor.

## Usage Examples

### 1. Single Consumer (Default)
```bash
python -m src.backend.doc_processing_system.messaging.document_processing.document_processor
```

### 2. Multiple Consumers via Command Line
```bash
# Start with 5 consumers
python -m src.backend.doc_processing_system.messaging.document_processing.document_processor --num-consumers 5

# Start with 8 consumers and custom directory
python -m src.backend.doc_processing_system.messaging.document_processing.document_processor --num-consumers 8 --watch-directory "data/documents/raw"
```

### 3. Multiple Consumers via Environment Variable
```bash
# Set environment variable
export DOC_PROCESSING_CONSUMERS=3

# Run with env variable (no need to specify --num-consumers)
python -m src.backend.doc_processing_system.messaging.document_processing.document_processor
```

### 4. Programmatic Usage
```python
from src.backend.doc_processing_system.messaging.document_processing.document_processor import DocumentProcessor

# Create processor with 4 consumers
processor = DocumentProcessor(
    watch_directory="data/documents/raw", 
    num_consumers=4
)

# Run the service
processor.run_forever()
```

## How It Works

- **Simple Threading**: Each consumer runs in its own thread
- **Unique Consumer Groups**: Each consumer gets a unique Kafka consumer group (`document_processing_consumer_1`, `document_processing_consumer_2`, etc.)
- **Shared Models**: All consumers share the same pre-loaded ML models (no duplicate loading)
- **Load Distribution**: Kafka automatically distributes messages across the consumer groups
- **Single File Watcher**: Only the first consumer handles file events to avoid duplicates
- **Graceful Shutdown**: All consumers stop cleanly on Ctrl+C

## Scaling Recommendations

Based on your Kafka topic partitions:
- **document-available** (6 partitions) → Use 6 consumers
- **extraction-tasks** (8 partitions) → Use 8 consumers  
- **chunking-complete** (4 partitions) → Use 4 consumers

Start with 3-6 consumers for most workloads.