# Vector Storage Task - Sequence Diagram

## Overview
The vector storage task handles the ingestion of embeddings from JSON files into Weaviate vector database. This diagram shows the complete flow from task initiation to successful storage.

## Sequence Diagram

```plantuml
@startuml Vector Storage Task Sequence
!define RECTANGLE class

participant "Prefect Task Runner" as Runner
participant "Vector Storage Task" as Task
participant "WeaviateIngestionEngine" as Engine
participant "WeaviateManager" as Manager
participant "CollectionManager" as Collections
participant "ConnectionManager" as Connection
participant "Weaviate Server" as Weaviate

== Task Initialization ==
Runner -> Task: store_vectors_task(embeddings_file_path, collection_name)
activate Task

Task -> Task: validate_file_exists()
Task -> Task: get_file_size()
Task -> Engine: WeaviateIngestionEngine()
activate Engine

Engine -> Manager: WeaviateManager()
activate Manager

Manager -> Collections: CollectionManager(connection_manager)
activate Collections
Manager -> Connection: ConnectionManager("localhost:8080")
activate Connection

== File Processing ==
Task -> Engine: ingest_from_embeddings_file(file_path, collection_name)

Engine -> Engine: _load_json_file(file_path)
Engine -> Engine: detect_format() 
note right: Checks for "validated_embeddings" vs "chromadb_ready"

alt validated_embeddings format
    Engine -> Engine: _ingest_validated_embeddings()
else chromadb_ready format  
    Engine -> Engine: _store_in_weaviate()
end

== Collection Management ==
Engine -> Manager: get_collection(collection_name)
Manager -> Collections: get_or_create_collection(collection_name)
Collections -> Connection: get_client()
Connection -> Weaviate: establish_connection()
Weaviate --> Connection: client_instance
Connection --> Collections: weaviate_client

Collections -> Weaviate: collections.get(collection_name)
alt collection exists
    Weaviate --> Collections: existing_collection
    Collections -> Collections: _validate_collection()
    Collections -> Weaviate: collection.aggregate.over_all(total_count=True)
    Weaviate --> Collections: validation_response
else collection not found
    Collections -> Collections: _create_collection()
    Collections -> Weaviate: collections.create(schema)
    Weaviate --> Collections: new_collection
    Collections -> Collections: _validate_collection()
end

Collections --> Manager: validated_collection
Manager --> Engine: collection_instance

== Data Ingestion ==
Engine -> Engine: process_validated_embeddings(69_embeddings)

loop for each embedding batch (100 objects)
    Engine -> Engine: convert_to_weaviate_objects()
    Engine -> Weaviate: collection.batch.add_object(properties, vector)
    Weaviate --> Engine: batch_response
end

Engine -> Engine: check_failed_objects()
alt no failures
    Engine -> Engine: log_success("Successfully stored 69 objects")
else has failures  
    Engine -> Engine: evaluate_failure_rate()
    alt failure_rate < 10%
        Engine -> Engine: log_warning("Some failures but acceptable")
    else failure_rate >= 10%
        Engine -> Engine: log_error("Too many failures")
        Engine --> Task: return False
    end
end

== Statistics Collection ==
Engine -> Engine: get_ingestion_stats(collection_name)
Engine -> Manager: get_collection_info(collection_name)
Manager -> Collections: get_collection_info(collection_name)
Collections -> Weaviate: collection.aggregate.over_all(total_count=True)
Weaviate --> Collections: count_response
Collections --> Manager: collection_info
Manager --> Engine: enhanced_stats

== Task Completion ==
Engine --> Task: success=True
Task -> Task: prepare_result_dict()
Task -> Task: log_completion_stats()

deactivate Connection
deactivate Collections  
deactivate Manager
deactivate Engine

Task --> Runner: result_dict{storage_status: "success", vectors_stored: True, document_count: 69}
deactivate Task

@enduml
```

## Key Flow Points

### 1. **File Validation & Loading**
- Task validates embeddings file exists and gets size
- Engine loads and parses JSON content
- Format detection determines processing path

### 2. **Collection Management** 
- Manager delegates to CollectionManager for collection operations
- ConnectionManager handles Weaviate client lifecycle
- Collections are created with BYOV (Bring Your Own Vectors) configuration
- Validation ensures collection is accessible before proceeding

### 3. **Data Processing Pipeline**
- `validated_embeddings` format: Direct property mapping
- `chromadb_ready` format: Format conversion then ingestion
- Batch processing with configurable batch size (100 objects)
- Error tolerance: Up to 10% failures acceptable

### 4. **Critical Error Handling**
- Collection validation failures trigger recreation
- UUID format issues resolved by auto-generation
- Batch failures monitored with early termination on excessive errors
- Connection errors bubble up with proper cleanup

### 5. **Statistics & Completion**
- Real-time document counting via Weaviate aggregation
- Comprehensive result dictionary with timing metrics
- Success/failure status with detailed error information

## Performance Characteristics

- **Processing Time**: ~2.6 seconds for 69 embeddings (4.4MB file)
- **Batch Size**: 100 objects per batch for optimal throughput
- **Memory Usage**: Streaming JSON processing, minimal memory footprint
- **Error Tolerance**: Up to 10% failure rate before task fails
- **Connection Pooling**: Single connection per ingestion session

## Error Recovery Patterns

1. **Collection Not Found** → Auto-create with proper schema
2. **Collection Validation Failed** → Recreate and validate
3. **Invalid UUID Format** → Let Weaviate auto-generate UUIDs
4. **Batch Import Errors** → Continue if failure rate < 10%
5. **Connection Issues** → Proper cleanup and error propagation