# Task-Message Mapping Implementation

## System Overview

The goal is to integrate the 7 sequential document processing tasks with the Kafka messaging system, creating an event-driven pipeline that starts from file detection and flows through complete document processing with vector storage.

## Current System Components

### Document Processing Pipeline (Sequential Tasks)
1. `duplicate_detection_task` - Check for document duplicates using content hash
2. `docling_processing_task` - Extract markdown and images using DoclingProcessor
3. `markdown_vision_task` - Process images with vision AI and enhance markdown
4. `chonkie_chunking_task` - Create semantic chunks with embeddings using ChonkieTwoStageChunker
5. `document_saving_task` - Save processed document to structured directory
6. `kafka_message_preparation_task` - Prepare Kafka messages for downstream pipelines
7. `weaviate_storage_task` - Store embedded chunks in Weaviate vector database

### Kafka Event Types (from event_bus.py)
- `FILE_DETECTED` - File system watcher detects new document
- `DOCUMENT_AVAILABLE` - Document ready for processing
- `WORKFLOW_INITIALIZED` - Processing workflow started
- `CHUNKING_COMPLETE` - Document chunking finished
- `EMBEDDING_READY` - Embeddings generated for chunks
- `INGESTION_COMPLETE` - Document fully ingested into vector store
- `FIELD_INIT_COMPLETE` - Field initialization complete
- `AGENT_SCALING_COMPLETE` - Agent scaling complete
- `EXTRACTION_TASKS` - Extraction tasks created
- `EXTRACTION_COMPLETE` - Extraction process finished
- `QUERY_RECEIVED` - Query received for processing
- `RAG_QUERY_COMPLETE` - RAG query processing complete
- `STRUCTURED_QUERY_COMPLETE` - Structured query complete
- `HYBRID_QUERY_COMPLETE` - Hybrid query complete

### Existing Messaging Infrastructure
- `FileWatcherService` - Already publishes `FILE_DETECTED` events
- `DocumentProducer` - Handles document-related event publishing
- `BaseKafkaConsumer/Producer` - Abstract base classes for Kafka operations
- `EventBus` - Central routing for all event types

## Task-to-Event Mapping Strategy

### Entry Point: File Detection Flow
```
FileWatcherService (file_watcher.py)
    ↓ publishes FILE_DETECTED event
DocumentProcessingConsumer (NEW)
    ↓ consumes FILE_DETECTED, triggers processing flow
DocumentFlowOrchestrator (NEW)
    ↓ coordinates tasks and event publishing
```

### Sequential Task-Event Flow
```
1. FILE_DETECTED (from file_watcher)
    ↓
2. duplicate_detection_task → DOCUMENT_AVAILABLE event
    ↓
3. docling_processing_task → WORKFLOW_INITIALIZED event
    ↓
4. markdown_vision_task → Custom VISION_PROCESSING_COMPLETE event
    ↓
5. chonkie_chunking_task → CHUNKING_COMPLETE + EMBEDDING_READY events
    ↓
6. document_saving_task → Custom DOCUMENT_SAVED event
    ↓
7. kafka_message_preparation_task → Custom KAFKA_MESSAGE_READY event
    ↓
8. weaviate_storage_task → INGESTION_COMPLETE event
```

### Event Data Contracts

#### FILE_DETECTED Event (existing)
```json
{
  "file_path": "/path/to/document.pdf",
  "filename": "document.pdf",
  "file_size": 1234567,
  "file_extension": ".pdf",
  "detected_at": "2024-01-15T10:30:00Z",
  "event_type": "file_detected"
}
```

#### DOCUMENT_AVAILABLE Event
```json
{
  "document_id": "uuid-string",
  "status": "ready_for_processing|duplicate|error",
  "file_path": "/path/to/document.pdf",
  "user_id": "default",
  "timestamp": "2024-01-15T10:30:01Z"
}
```

#### WORKFLOW_INITIALIZED Event
```json
{
  "document_id": "uuid-string",
  "workflow_types": ["rag", "extraction"],
  "status": "initialized",
  "processed_markdown_path": "/path/to/document.md",
  "extracted_images_dir": "/path/to/images/",
  "file_info": {...}
}
```

#### CHUNKING_COMPLETE Event
```json
{
  "document_id": "uuid-string",
  "chunk_count": 25,
  "embedding_model": "nomic-ai/nomic-embed-text-v1.5",
  "chunking_strategy": "chonkie_two_stage_semantic_boundary",
  "chunking_params": {...}
}
```

#### EMBEDDING_READY Event
```json
{
  "document_id": "uuid-string",
  "embedded_chunks": [...],
  "embedding_dimensions": 768,
  "embedding_model": "nomic-ai/nomic-embed-text-v1.5"
}
```

#### INGESTION_COMPLETE Event
```json
{
  "document_id": "uuid-string",
  "collection_name": "rag_documents",
  "chunks_stored": 25,
  "weaviate_url": "http://localhost:8080",
  "storage_timestamp": "2024-01-15T10:35:00Z"
}
```

## Implementation Components

### 1. DocumentProcessingConsumer
- Inherits from `BaseKafkaConsumer`
- Subscribes to `file-detected` topic
- Triggers `DocumentFlowOrchestrator` on message receipt
- Handles consumer group management and error handling

### 2. DocumentFlowOrchestrator
- Wraps existing `document_processing_flow.py`
- Accepts Kafka producer as dependency
- Coordinates between Prefect tasks and Kafka event publishing
- Publishes events after each task completion
- Maintains error handling and retry logic

### 3. Enhanced Tasks
Each task will be modified to:
- Accept optional Kafka producer parameter
- Publish completion events with appropriate payloads
- Include task-specific metadata in events
- Maintain backward compatibility (producer=None by default)

### 4. Event Publishing Strategy
- Use existing `DocumentProducer` for standard events
- Create custom event types for task-specific completions
- Ensure idempotent publishing (handle duplicates)
- Include correlation IDs for event tracing

## Error Handling Strategy

### Task Failure Events
```json
{
  "document_id": "uuid-string",
  "task_name": "chonkie_chunking_task",
  "status": "error",
  "error_message": "Chunking failed: insufficient memory",
  "retry_count": 2,
  "timestamp": "2024-01-15T10:32:00Z"
}
```

### Retry Logic
- Consumer-level retries for transient failures
- Dead letter queue for persistent failures
- Exponential backoff for retry intervals
- Maximum retry limits per task type

## Integration Points

### With Existing System
- File watcher continues to work unchanged
- Prefect flows maintain their orchestration role
- Tasks remain functional without Kafka (backward compatibility)
- Existing data models and validation continue to work

### With Future Components
- Query processing can subscribe to INGESTION_COMPLETE events
- Monitoring systems can track event flow
- Additional consumers can be added for specific workflows
- Event replay capabilities for system recovery

## Testing Strategy

### Unit Tests
- Mock Kafka producer in task tests
- Verify event payloads match contracts
- Test error scenarios and retry logic

### Integration Tests
- End-to-end file detection to ingestion flow
- Verify all events are published in correct sequence
- Test consumer error handling and recovery

### Performance Tests
- Measure event processing latency
- Test throughput with multiple concurrent documents
- Verify system stability under load

## Success Criteria

1. **Event Flow Completeness**: All 7 tasks publish appropriate events
2. **Data Integrity**: Event payloads contain all necessary information for downstream consumers
3. **Error Resilience**: System gracefully handles task failures and publishes error events
4. **Backward Compatibility**: Existing functionality works unchanged when Kafka is disabled
5. **Performance**: Event publishing adds minimal overhead to task execution
6. **Monitoring**: Clear event trail in Kafka topics for debugging and observability

## Implementation Timeline

### Phase 1: Documentation and Design
- ✅ Create this requirements document
- Define detailed event schemas
- Review with team

### Phase 2: Core Components
- Create `DocumentProcessingConsumer`
- Create `DocumentFlowOrchestrator` 
- Set up basic event publishing flow

### Phase 3: Task Integration
- Modify each task to publish events
- Add error event publishing
- Implement retry logic

### Phase 4: Testing and Validation
- Unit tests for all components
- Integration test for full flow
- Performance testing and optimization

This implementation will create a robust, event-driven document processing system that maintains existing functionality while enabling future scalability and monitoring capabilities.