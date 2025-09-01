# RAG Pipeline Refactoring Plan - Decoupled Kafka Architecture

## Current Problem
Currently, the RAG consumer triggers the ENTIRE flow at once when it receives `document-available` messages. This prevents individual scaling and creates a monolithic processing block.

## Target Architecture
Each processing stage should be an independent Kafka consumer that can be scaled separately:

```
document-available → chunking_consumer → chunking-complete → embedding_consumer → embedding-ready → storage_consumer → ingestion-complete
```

## Implementation Plan

### Phase 1: Create Individual Stage Consumers

#### 1.1 Chunking Consumer
**File**: `src/backend/doc_processing_system/pipelines/rag_processing/flows/consumers/chunking_consumer.py`
- **Listens to**: `document-available`  
- **Executes**: `semantic_chunking_task` → `boundary_refinement_task` → `chunk_formatting_task`
- **Publishes to**: `chunking-complete`
- **Message Format**:
```json
{
  "document_id": "doc_123",
  "chunks_file_path": "data/rag/chunks/chunks_doc_123_timestamp.json",
  "chunk_count": 15,
  "processing_time": 2.75,
  "event_type": "chunking_complete",
  "timestamp": "2025-09-01T12:30:45"
}
```

#### 1.2 Embedding Consumer  
**File**: `src/backend/doc_processing_system/pipelines/rag_processing/flows/consumers/embedding_consumer.py`
- **Listens to**: `chunking-complete`
- **Executes**: `generate_embeddings_task`
- **Publishes to**: `embedding-ready`  
- **Message Format**:
```json
{
  "document_id": "doc_123",
  "embeddings_file_path": "data/rag/embeddings/embeddings_doc_123_timestamp.json",
  "embeddings_count": 15,
  "model_used": "BAAI/bge-large-en-v1.5",
  "processing_time": 1.2,
  "event_type": "embedding_ready",
  "timestamp": "2025-09-01T12:32:00"
}
```

#### 1.3 Vector Storage Consumer
**File**: `src/backend/doc_processing_system/pipelines/rag_processing/flows/consumers/storage_consumer.py`
- **Listens to**: `embedding-ready`
- **Executes**: `store_vectors_task`
- **Publishes to**: `ingestion-complete`
- **Message Format**:
```json
{
  "document_id": "doc_123", 
  "collection_name": "rag_documents",
  "vectors_stored": true,
  "collection_stats": {"document_count": 150},
  "processing_time": 0.8,
  "event_type": "ingestion_complete",
  "timestamp": "2025-09-01T12:32:45"
}
```

### Phase 2: Update Task Imports and Dependencies

#### 2.1 Fix Task Imports
**File**: `src/backend/doc_processing_system/pipelines/rag_processing/flows/tasks/__init__.py`
- Export all individual tasks for consumer use
- Ensure proper import paths

#### 2.2 Update Task Dependencies
**Files**: `src/backend/doc_processing_system/pipelines/rag_processing/flows/tasks/*.py`
- Remove any flow-level dependencies
- Ensure tasks can run independently  
- Validate input/output formats for Kafka message compatibility

### Phase 3: Create Producer Utilities

#### 3.1 RAG Stage Producers
**File**: `src/backend/doc_processing_system/pipelines/rag_processing/flows/producers/rag_stage_producers.py`
- `publish_chunking_complete()`
- `publish_embedding_ready()`  
- `publish_ingestion_complete()`
- Centralized producer functions for consistency

### Phase 4: Consumer Group Configuration

#### 4.1 Consumer Group Setup
Each consumer should have its own consumer group for independent scaling:
- `chunking_consumer` → `"rag_chunking_group"`
- `embedding_consumer` → `"rag_embedding_group"` 
- `storage_consumer` → `"rag_storage_group"`

#### 4.2 Scaling Configuration
**File**: `src/backend/doc_processing_system/pipelines/rag_processing/flows/scaling_config.py`
- Define default scaling parameters for each stage
- Allow environment-based configuration overrides

### Phase 5: Remove Monolithic Flow

#### 5.1 Deprecate Current RAG Consumer
**File**: `src/backend/doc_processing_system/pipelines/rag_processing/flows/rag_consumer.py`
- Mark as deprecated
- Replace with stage-specific consumers
- Keep temporarily for migration testing

#### 5.2 Update RAG Processing Flow
**File**: `src/backend/doc_processing_system/pipelines/rag_processing/flows/rag_processing_flow.py`  
- Remove Kafka publishing from flow (now handled by individual consumers)
- Keep flow for testing/development use only
- Simplify to pure task orchestration

### Phase 6: Service Orchestration Files

#### 6.1 Consumer Management
**File**: `src/backend/doc_processing_system/pipelines/rag_processing/flows/services/consumer_manager.py`
- Start/stop all RAG consumers as a group
- Health monitoring for each consumer
- Graceful shutdown coordination

#### 6.2 Service Entry Points
**Files**: 
- `src/backend/doc_processing_system/pipelines/rag_processing/flows/services/start_chunking_consumer.py`
- `src/backend/doc_processing_system/pipelines/rag_processing/flows/services/start_embedding_consumer.py` 
- `src/backend/doc_processing_system/pipelines/rag_processing/flows/services/start_storage_consumer.py`

## File Structure After Refactoring

```
src/backend/doc_processing_system/pipelines/rag_processing/flows/
├── REFACTORING_PLAN.md                    # This plan
├── tasks/                                  # Individual task implementations
│   ├── __init__.py                        # Export all tasks
│   ├── semantic_chunking_task.py          # ✅ Already exists
│   ├── boundary_refinement_task.py        # ✅ Already exists  
│   ├── chunk_formatting_task.py           # ✅ Already exists
│   ├── generate_embeddings_task.py        # ✅ Already exists
│   └── store_vectors_task.py              # ✅ Already exists
├── consumers/                             # 🆕 Stage-specific consumers
│   ├── __init__.py                        # Export all consumers
│   ├── chunking_consumer.py               # 🆕 document-available → chunking-complete
│   ├── embedding_consumer.py              # 🆕 chunking-complete → embedding-ready  
│   └── storage_consumer.py                # 🆕 embedding-ready → ingestion-complete
├── producers/                             # 🆕 Kafka producers
│   ├── __init__.py                        # Export producers
│   └── rag_stage_producers.py            # 🆕 Centralized publishers
├── services/                              # 🆕 Service management
│   ├── __init__.py                        
│   ├── consumer_manager.py                # 🆕 Multi-consumer orchestration
│   ├── start_chunking_consumer.py         # 🆕 Chunking service entry
│   ├── start_embedding_consumer.py        # 🆕 Embedding service entry
│   └── start_storage_consumer.py          # 🆕 Storage service entry
├── scaling_config.py                      # 🆕 Scaling configuration
├── rag_processing_flow.py                 # ✅ Simplified (no Kafka)
└── rag_consumer.py                        # ⚠️ Deprecated (keep for migration)
```

## Benefits After Refactoring

### 1. **Independent Scaling**
- Scale chunking consumers for CPU-intensive semantic processing
- Scale embedding consumers for GPU/memory-intensive embedding generation  
- Scale storage consumers for I/O-intensive ChromaDB operations

### 2. **Fault Isolation** 
- Chunking failure doesn't affect embedding/storage stages
- Each stage can retry independently
- Better error handling and recovery

### 3. **Resource Optimization**
- Deploy chunking consumers on high-CPU nodes
- Deploy embedding consumers on GPU nodes  
- Deploy storage consumers on high-memory nodes

### 4. **Development & Testing**
- Test individual stages in isolation
- Easier debugging and monitoring
- Independent deployment of stage improvements

## Migration Strategy

1. **Phase 1**: Implement new consumers alongside existing flow
2. **Phase 2**: Deploy consumers in parallel (both systems running)
3. **Phase 3**: Route traffic gradually to new system
4. **Phase 4**: Remove old monolithic consumer
5. **Phase 5**: Clean up deprecated code

This approach ensures zero downtime during migration while enabling the desired scalable architecture.