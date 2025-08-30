# Data Flow Architecture Documentation

This directory contains the complete data flow architecture for the Scaled Processing System, organized by layer for better maintainability and understanding.

## 📁 Directory Structure

```
docs/data_flow/
├── system_dataflow_overview.puml       # High-level system overview
├── document_upload_dataflow.puml       # Document ingestion layer
├── rag_workflow_dataflow.puml          # RAG processing pipeline
├── structured_extraction_dataflow.puml # Structured extraction pipeline
├── query_processing_dataflow.puml      # Query handling & response
└── README.md                          # This file
```

## 🎯 Layer Overview

### 1. **System Overview** (`system_dataflow_overview.puml`)
- **Purpose**: High-level architecture showing how all layers interconnect
- **Shows**: Layer relationships, cross-layer data flows, key technologies
- **Use Case**: Understanding overall system architecture

### 2. **Document Upload Layer** (`document_upload_dataflow.puml`)
- **Purpose**: Document ingestion and initial processing
- **Models**: `UploadFile`, `DocumentMetadata`, `ParsedDocument`, `FileType`
- **Database**: `documents_table`, `document_metadata_table`
- **Messages**: `DocumentReceivedEvent`, `WorkflowInitializedEvent`
- **Key Functions**: File validation, dynamic parsing, parallel workflow triggers

### 3. **RAG Workflow Layer** (`rag_workflow_dataflow.puml`)
- **Purpose**: Vector processing pipeline for semantic search
- **Models**: `ChunkingRequest`, `TextChunk`, `ValidatedEmbedding`, `VectorSearchResult`
- **Database**: `chunks_table` (PostgreSQL), `document_embeddings` (ChromaDB)
- **Messages**: `ChunkingCompleteEvent`, `EmbeddingReadyEvent`, `IngestionCompleteEvent`
- **Key Functions**: Semantic chunking, embedding generation, vector storage

### 4. **Structured Extraction Layer** (`structured_extraction_dataflow.puml`)
- **Purpose**: Dynamic field discovery and structured data extraction
- **Models**: `FieldInitRequest`, `FieldSpecification`, `AgentScalingConfig`, `ExtractionResult`
- **Database**: `field_specifications_table`, `extracted_data_table`, `agent_scaling_logs_table`
- **Messages**: `FieldInitCompleteEvent`, `AgentScalingCompleteEvent`, `ExtractionTaskMessage`, `ExtractionCompleteEvent`
- **Key Functions**: Sequential field discovery, agent swarm scaling, structured data storage

### 5. **Query Processing Layer** (`query_processing_dataflow.puml`)
- **Purpose**: Multi-modal query handling and response generation
- **Models**: `UserQuery`, `RAGQueryResult`, `StructuredQueryResult`, `HybridQueryResult`
- **Database**: `query_logs_table`, `query_results_table`, `query_performance_table`
- **Messages**: `QueryReceivedEvent`, `RAGQueryCompleteEvent`, `StructuredQueryCompleteEvent`, `HybridQueryCompleteEvent`
- **Key Functions**: Query routing, result fusion, performance tracking

## 🔄 Data Flow Patterns

### Event-Driven Architecture
- **Kafka Topics**: Each layer publishes and consumes specific message types
- **Decoupling**: Layers communicate only through well-defined events
- **Scalability**: Independent scaling based on message volume per layer

### Database Strategy
- **PostgreSQL**: Structured data, metadata, query logs, performance metrics
- **ChromaDB**: Vector embeddings, similarity search, collection management
- **Data Consistency**: Event-driven updates with eventual consistency

### Cross-Layer Integration
- **Upload → RAG**: `DocumentReceivedEvent` triggers chunking pipeline
- **Upload → Extraction**: `DocumentReceivedEvent` triggers field discovery
- **RAG → Query**: Vector search integration for semantic queries
- **Extraction → Query**: Structured data filtering for field-based queries

## 🚀 Benefits of This Organization

1. **Modularity**: Each layer is independently documented and maintainable
2. **Clarity**: Focused diagrams reduce cognitive load
3. **Scalability**: Easy to understand scaling patterns per layer
4. **Development**: Clear contracts between layers for implementation
5. **Debugging**: Isolated data flows make troubleshooting easier

## 📋 Usage Guidelines

- **For Architecture Review**: Start with `system_dataflow_overview.puml`
- **For Implementation**: Use individual layer files for detailed models
- **For Debugging**: Follow data flow through specific layer diagrams
- **For Scaling**: Analyze message patterns in layer-specific diagrams

## 🔗 Related Documentation

- **Workflows**: `../workflows/` - Process flow diagrams
- **Architecture**: `../backend_structure.md` - Code organization
- **Components**: `../component.puml` - System components overview