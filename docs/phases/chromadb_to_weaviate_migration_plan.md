# ChromaDB to Weaviate Migration Plan

**Date:** September 2, 2025  
**Session Focus:** Complete migration from ChromaDB to Weaviate for stable vector operations  

## Executive Summary

After extensive troubleshooting with ChromaDB Windows compatibility issues and segmentation faults in the unified orchestrator environment, we are migrating to Weaviate as a more stable, production-ready vector database solution. This migration will eliminate the process isolation workarounds and provide a robust foundation for vector operations.

## Why Migrate from ChromaDB to Weaviate?

### Problems with ChromaDB
1. **Windows DLL Compatibility Issues**: Persistent segmentation faults (ACCESS_VIOLATION 0xc0000005) in multi-threaded environments
2. **Process Isolation Required**: Had to implement complex isolated worker processes to prevent system crashes
3. **Operational Complexity**: Requires extensive error handling and graceful failure recovery
4. **Thread Safety**: Known instability in concurrent environments with Kafka consumers
5. **Maintenance Overhead**: Constant debugging and workarounds for Windows-specific issues

### Benefits of Weaviate
1. **Production Stability**: Mature, battle-tested vector database with enterprise-grade reliability
2. **Excellent Windows Support**: No known DLL compatibility issues on Windows
3. **Docker Native**: Clean containerized deployment without process isolation hacks
4. **Bring Your Own Vectors (BYOV)**: Perfect for our custom embedding pipeline
5. **RESTful API**: Simple, predictable HTTP-based interface
6. **Better Performance**: Optimized for production workloads with superior scalability
7. **Rich Query Capabilities**: Advanced filtering and hybrid search features
8. **Active Development**: Regular updates and strong community support

## Current ChromaDB Integration Analysis

### Files Currently Using ChromaDB
Based on codebase analysis, ChromaDB is integrated in 17 files:

**Core Components:**
- `src/backend/doc_processing_system/core_deps/chromadb/chroma_manager.py` - Connection management
- `src/backend/doc_processing_system/core_deps/chromadb/chunk_ingestion_engine.py` - Data ingestion
- `src/backend/doc_processing_system/core_deps/chromadb/isolated_chromadb_worker.py` - Process isolation workaround

**Pipeline Integration:**
- `src/backend/doc_processing_system/pipelines/rag_processing/flows/tasks/vector_storage_task.py` - Storage task
- `src/backend/doc_processing_system/pipelines/rag_processing/flows/tasks/embeddings_generation_task.py` - Embeddings
- `src/backend/doc_processing_system/messaging/rag_pipeline/storage_consumer.py` - Kafka consumer

**Service Layer:**
- `src/backend/doc_processing_system/services/unified_orchestrator.py` - Main orchestrator
- `src/backend/doc_processing_system/services/rag/rag_orchestrator.py` - RAG operations

## Weaviate Architecture Design - Drop-in Replacement Strategy

### Key Insight: Interface Compatibility
Instead of changing the entire pipeline, we'll create Weaviate components that offer **exactly the same interface** as the existing ChromaDB components. This means:
- No changes to pipeline tasks, orchestrators, or consumers
- No changes to existing function calls or APIs  
- Just swap the underlying implementation from ChromaDB to Weaviate

### Docker Configuration
Already configured in `docker-compose.yml` with BYOV support:
```yaml
weaviate:
  image: cr.weaviate.io/semitechnologies/weaviate:1.32.4
  environment:
    DEFAULT_VECTORIZER_MODULE: 'none'  # Essential for BYOV
    AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
    PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
```

### Drop-in Replacement Components

#### 1. Weaviate Manager (`weaviate_manager.py`)
**Same interface as `chroma_manager.py`:**
```python
class WeaviateManager:
    """Drop-in replacement for ChromaManager with identical interface."""
    
    def __init__(self, persist_directory: str = None, collection_name: str = "rag_documents"):
        # Same constructor signature as ChromaManager
    
    def get_client(self) -> Optional[weaviate.WeaviateClient]:
        # Same interface as ChromaManager.get_client()
    
    def get_collection(self, collection_name: str = "rag_documents"):
        # Same interface as ChromaManager.get_collection()
    
    def get_collection_info(self, collection_name: str = "rag_documents") -> Optional[Dict[str, Any]]:
        # Same interface as ChromaManager.get_collection_info()
    
    def list_collections(self) -> List[str]:
        # Same interface as ChromaManager.list_collections()
    
    def delete_collection(self, collection_name: str) -> bool:
        # Same interface as ChromaManager.delete_collection()
    
    def reset_database(self) -> bool:
        # Same interface as ChromaManager.reset_database()
```

#### 2. Weaviate Ingestion Engine (`weaviate_ingestion_engine.py`) 
**Same interface as `chunk_ingestion_engine.py` with generic naming:**
```python
class WeaviateIngestionEngine:
    """Drop-in replacement for ChunkIngestionEngine with identical interface."""
    
    def __init__(self):
        # Same constructor as ChunkIngestionEngine
    
    def ingest_from_embeddings_file(self, embeddings_file_path: str, collection_name: str = "rag_documents") -> bool:
        # Same interface - accepts standard embeddings format, processes internally for Weaviate
        # Returns same boolean success/failure as ChromaDB version
        # (Renamed from ingest_from_chromadb_ready_file to be database-agnostic)
    
    def get_ingestion_stats(self, collection_name: str = "rag_documents") -> Dict[str, Any]:
        # Same interface as ChunkIngestionEngine.get_ingestion_stats()
        # Returns same format as ChromaDB version
```

#### 3. No Isolated Worker Needed
Since Weaviate doesn't have segmentation fault issues, we can **eliminate** the `isolated_chromadb_worker.py` completely. The vector storage task will call the ingestion engine directly.

### Data Format Compatibility

#### Current ChromaDB Format (chromadb_ready):
```json
{
    "ids": ["doc1_chunk1", "doc1_chunk2"],
    "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]],
    "metadatas": [{"source": "doc1", "page": 1}, ...],
    "documents": ["chunk text 1", "chunk text 2"]
}
```

#### New Weaviate Format (weaviate_ready):
```json
{
    "objects": [
        {
            "id": "doc1_chunk1",
            "properties": {
                "content": "chunk text 1",
                "source": "doc1",
                "page": 1
            },
            "vector": [0.1, 0.2, ...]
        }
    ]
}
```

## Simplified Migration Strategy - Drop-in Replacement

### Phase 1: Create Drop-in Components (2-3 Days)
**Goal**: Create Weaviate components with identical interfaces to ChromaDB components

**Tasks**:
1. **Create Weaviate Manager**
   - `src/backend/doc_processing_system/core_deps/weaviate/weaviate_manager.py`
   - Implement exact same interface as `ChromaManager`
   - Same method signatures, same return types, same behavior

2. **Create Weaviate Ingestion Engine**
   - `src/backend/doc_processing_system/core_deps/weaviate/weaviate_ingestion_engine.py`
   - Implement exact same interface as `ChunkIngestionEngine`
   - Accept chromadb_ready format, convert internally to Weaviate format

3. **Add Weaviate Client Dependency**
   - Add `weaviate-client>=4.16.9` to requirements
   - Test connection to local Weaviate instance (already in docker-compose.yml)

4. **Internal Data Format Conversion**
   - Build chromadb_ready → Weaviate format converter inside ingestion engine
   - Handle metadata mapping and vector extraction internally
   - Keep existing pipeline data format unchanged

**Deliverables**:
- `WeaviateManager` class with ChromaManager interface
- `WeaviateIngestionEngine` class with ChunkIngestionEngine interface
- Working connection to local Weaviate
- Internal format conversion

### Phase 2: Swap Implementation (1 Day)  
**Goal**: Replace ChromaDB imports with Weaviate imports

**Tasks**:
1. **Update Import Statements Only**
   - Change imports in files that use ChromaDB components
   - Replace `from ...chromadb.chroma_manager import ChromaManager` 
   - With `from ...weaviate.weaviate_manager import WeaviateManager as ChromaManager`
   - Replace `from ...chromadb.chunk_ingestion_engine import ChunkIngestionEngine`
   - With `from ...weaviate.weaviate_ingestion_engine import WeaviateIngestionEngine as ChunkIngestionEngine`

2. **Remove Isolated Worker Usage**
   - Update `vector_storage_task.py` to call ingestion engine directly
   - Remove `get_isolated_chromadb_worker()` calls
   - Use direct `get_chunk_ingestion_engine()` calls (which now returns Weaviate engine)

3. **No Other Changes Needed**
   - ✅ All existing pipeline tasks work as-is
   - ✅ All orchestrators work as-is  
   - ✅ All consumers work as-is
   - ✅ All API endpoints work as-is

**Deliverables**:
- Updated import statements only
- Eliminated isolated worker dependency
- **Zero changes to business logic or pipeline flow**

### Phase 3: Testing & Data Migration (2-3 Days)
**Goal**: Validate functionality and migrate existing data

**Tasks**:
1. **Functional Testing**
   - Test all existing pipeline operations
   - Validate vector storage and retrieval
   - Ensure all existing APIs work correctly

2. **Data Migration Script**
   - Create utility to transfer existing ChromaDB data → Weaviate
   - Migrate vectors from ChromaDB collections to Weaviate collections
   - Validate migrated data integrity

3. **Performance Validation**
   - Compare ingestion performance
   - Compare query response times
   - Optimize batch sizes if needed

**Deliverables**:
- Fully tested system with Weaviate backend
- Migrated data from ChromaDB
- Performance benchmarks

### Phase 4: Cleanup (1 Day)
**Goal**: Remove ChromaDB dependencies and unused code

**Tasks**:
1. **Remove ChromaDB Files**
   - Delete `src/backend/doc_processing_system/core_deps/chromadb/` directory
   - Remove `chromadb` from requirements
   - Remove `chromadb` service from docker-compose.yml

2. **Archive Reference Implementation**
   - Keep isolated worker solution as reference in docs
   - Document lessons learned for future reference

**Deliverables**:
- Clean codebase without ChromaDB
- Archived reference documentation

## Key Benefits of This Approach

### Minimal Risk
- ✅ **No pipeline changes**: All existing flow logic remains identical
- ✅ **No API changes**: All endpoints continue to work
- ✅ **No schema changes**: Data formats remain compatible
- ✅ **Easy rollback**: Just change imports back if needed

### Faster Implementation
- ⏱️ **Total time: 5-7 days** instead of 4 weeks
- ⏱️ **Parallel development**: Can build alongside existing system
- ⏱️ **Incremental testing**: Test each component independently

### Clean Architecture
- 🏗️ **Interface segregation**: Clear separation between interface and implementation
- 🏗️ **Dependency inversion**: High-level modules don't change
- 🏗️ **Single responsibility**: Each component has one job

### BYOV Configuration
To insert many objects using the "Bring Your Own Vector" (BYOV) feature with a **local Weaviate instance**, you should:

1. **Connect to your local Weaviate instance.**
2. **Create or use a collection configured for self-provided vectors.**
3. **Batch import your objects, providing the vector for each object at the top level (not inside properties).**

Here’s a step-by-step example using the Python client v4:

---

### 1. Connect to Local Weaviate

```python
import weaviate

client = weaviate.connect_to_local()
```
[Reference](https://docs.weaviate.io/weaviate/connections/connect-local)

---

### 2. Create a Collection for BYOV

```python
from weaviate.classes.config import Configure, Property, DataType

collection_name = "DemoCollection"

client.collections.create(
    collection_name,
    vector_config=[
        Configure.Vectors.self_provided(),  # Use self-provided vectors
    ],
    properties=[
        Property(name="text", data_type=DataType.TEXT),
        Property(name="docid", data_type=DataType.TEXT),
    ],
)
```
[Reference](https://docs.weaviate.io/weaviate/tutorials/multi-vector-embeddings#option-2-user-provided-embeddings)

---

### 3. Batch Insert with Your Own Vectors

Suppose you have your data and vectors:

```python
data_rows = [
    {"text": "Weaviate is a vector database.", "docid": "doc1"},
    {"text": "PyTorch is a deep learning framework.", "docid": "doc2"},
]
vectors = [
    [0.1, 0.2, 0.3],  # Example vector for doc1
    [0.4, 0.5, 0.6],  # Example vector for doc2
]

collection = client.collections.use(collection_name)

with collection.batch.fixed_size(batch_size=100) as batch:
    for i, data_row in enumerate(data_rows):
        batch.add_object(
            properties=data_row,
            vector=vectors[i]
        )
        if batch.number_errors > 10:
            print("Batch import stopped due to excessive errors.")
            break

failed_objects = collection.batch.failed_objects
if failed_objects:
    print(f"Number of failed imports: {len(failed_objects)}")
    print(f"First failed object: {failed_objects[0]}")
```
[Reference](https://docs.weaviate.io/weaviate/manage-objects/import#specify-a-vector)

---

**Key Points:**
- The `vector` must be provided at the top level of each object, not inside `properties`.
- Use the batch context manager for efficient and reliable imports.
- Always check for failed objects after the batch import.

This approach is fully supported and recommended for BYOV with a local Weaviate instance.
---
1. **Generate the query embedding using your local model** (the same model you used to generate the stored vectors).
2. **Send the query vector to Weaviate** using a `near_vector` search.
---

### 1. Generate the Query Vector

Use your local embedding model to convert your query text into a vector. For example, if you use a Hugging Face or Cohere model locally, call your model’s embedding function to get the vector.

```python
# Example: Using a local Cohere model (replace with your own model as needed)
def vectorize(text):
    # Replace this with your local model's embedding logic
    return [0.1, 0.2, 0.3]  # Example vector
```

---

### 2. Query Weaviate with the Vector

Use the Python client to perform a vector search by passing the query vector to `near_vector`. Here’s a minimal example:

```python
import weaviate

client = weaviate.connect_to_local()
collection = client.collections.get("YourCollectionName")

query_text = "your search text"
query_vector = vectorize(query_text)  # Use your local model here

response = collection.query.near_vector(
    near_vector=query_vector,
    limit=5,
)

for obj in response.objects:
    print(obj.properties)
```

This approach is required because, with BYOV, Weaviate does not know how to convert your query text into a vector—so you must do it yourself and provide the vector directly. This is confirmed in the documentation:  
> "Note that `near text` search is not possible with user-provided embeddings. In this configuration, Weaviate is unable to convert a text query into a compatible embedding, without knowing the model used to generate the embeddings."  
[See source](https://docs.weaviate.io/weaviate/tutorials/multi-vector-embeddings#24-perform-queries)
---
**Summary:**  
- Use your local embedding model to generate the query vector.
- Use Weaviate’s `near_vector` search, passing your query vector directly.
- This works with a local Weaviate instance and BYOV collections.
For more details and code samples, see the [official BYOV quickstart guide](https://docs.weaviate.io/weaviate/starter-guides/custom-vectors#query) and [multi-vector tutorial](https://docs.weaviate.io/weaviate/tutorials/multi-vector-embeddings#24-perform-queries).
### Error Handling Strategy
Unlike ChromaDB's segmentation faults, Weaviate provides predictable HTTP-based errors:
```python
try:
    result = collection.data.insert(obj)
except weaviate.exceptions.WeaviateConnectionError:
    # Connection issues - retry logic
except weaviate.exceptions.WeaviateQueryError:
    # Query/data issues - validate and log
except Exception as e:
    # Unexpected errors - log and continue
```

## Risk Mitigation

### 1. Parallel Development
- Develop Weaviate components alongside existing ChromaDB system
- Test thoroughly before switching production traffic
- Maintain ChromaDB as fallback during initial deployment

### 2. Data Integrity
- Implement comprehensive data validation during migration
- Create checksums/hashes to verify data transfer accuracy  
- Run side-by-side testing to compare query results

### 3. Performance Monitoring
- Monitor query response times during migration
- Compare ingestion performance between ChromaDB and Weaviate
- Set up alerting for performance degradation

### 4. Rollback Strategy
- Keep ChromaDB components until Weaviate is fully validated
- Create migration rollback procedures
- Maintain data backups throughout migration

## Expected Benefits After Migration

### 1. System Stability
- ✅ **No more segmentation faults**: Eliminate Windows DLL compatibility issues
- ✅ **Simplified architecture**: Remove complex process isolation workarounds
- ✅ **Predictable errors**: HTTP-based error handling instead of process crashes

### 2. Operational Excellence  
- ✅ **Better monitoring**: Rich HTTP metrics and health endpoints
- ✅ **Easier debugging**: Clear error messages and request tracing
- ✅ **Reduced maintenance**: No more isolated worker processes to manage

### 3. Performance Improvements
- ✅ **Faster operations**: Native multi-threading without crash risks
- ✅ **Better scaling**: Production-grade horizontal scaling capabilities
- ✅ **Optimized queries**: Advanced filtering and hybrid search features

### 4. Developer Experience
- ✅ **Cleaner code**: Remove complex error handling and recovery logic
- ✅ **Better documentation**: Comprehensive Weaviate documentation and examples
- ✅ **Easier testing**: Predictable behavior and reliable test environments

## Timeline Summary

| Days | Phase | Focus | Key Deliverables |
|------|--------|--------|------------------|
| 2-3 | Drop-in Components | Interface compatibility | Weaviate manager, ingestion engine with ChromaDB interface |
| 1 | Import Swap | Change imports only | Updated imports, removed isolated worker |
| 2-3 | Testing & Migration | Validation & data | Functional tests, data migration, performance validation |
| 1 | Cleanup | Remove old code | ChromaDB removal, documentation |

**Total Timeline: 5-7 days** (compared to 4 weeks with the original approach)

## Success Criteria

### Technical Success
- [ ] All ChromaDB functionality replicated in Weaviate
- [ ] No segmentation faults or process isolation requirements
- [ ] Performance equal or better than ChromaDB (when working)
- [ ] Complete data migration with integrity validation

### Operational Success  
- [ ] Unified orchestrator runs stable without crashes
- [ ] All RAG pipeline operations working smoothly
- [ ] Monitoring and alerting in place
- [ ] Team trained on Weaviate operations

### Business Success
- [ ] Zero downtime migration
- [ ] Improved system reliability and user experience
- [ ] Reduced operational overhead and maintenance costs
- [ ] Platform ready for future scaling requirements

## Conclusion

This **drop-in replacement migration** from ChromaDB to Weaviate represents a strategic shift from managing compatibility issues to leveraging a production-ready vector database. The key insight is using **interface compatibility** to minimize changes and risk.

### The Simplified Approach Benefits:

1. **Minimal Risk**: Only imports change, all business logic stays identical
2. **Fast Implementation**: 5-7 days instead of 4 weeks
3. **Easy Rollback**: Just change imports back if issues arise
4. **Zero Downtime**: Can develop and test in parallel with existing system

### Technical Transformation:

**Before (ChromaDB):**
- Segmentation faults requiring process isolation
- Complex isolated worker processes
- Unpredictable crashes and error handling
- Windows DLL compatibility issues

**After (Weaviate):**
- Direct HTTP-based operations, no crashes
- Clean, simple ingestion without isolation
- Predictable error handling and debugging
- Production-grade stability and performance

### Implementation Strategy:

By creating `WeaviateManager` and `WeaviateIngestionEngine` with **identical interfaces** to their ChromaDB counterparts, we eliminate the need to change any pipeline, orchestrator, or consumer code. The system will function identically from the outside while being completely transformed on the inside.

This approach transforms our vector database layer from a **source of system instability** into a **reliable foundation for growth** in just one week, enabling the team to focus on features rather than infrastructure workarounds.

**Result**: A production-ready, crash-free vector database solution that maintains 100% compatibility with existing code.