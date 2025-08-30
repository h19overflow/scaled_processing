# Architecture Roadmap: Prefect Pipeline Implementation

## 🎯 **Priority Sequence (Sprint 2+)**

### **Phase 1: Document Processing Pipeline (Foundation)**
```
Document Upload → Document Parser → Structured Content
                                ↓
                        Two Parallel Pipelines:
                         ↓              ↓
                   RAG Pipeline    Extraction Pipeline
```

**Why First:** All downstream processing depends on clean, parsed document content.

**🚀 Docling Advantage:** Using Docling for unified document processing provides:
- **Single API** for PDF, DOCX, and Image processing
- **Consistent output format** across all document types
- **Built-in structure detection** (tables, headings, sections)
- **Simplified architecture** - no need for multiple parsers
- **Better maintainability** - one processing pipeline to maintain

**Core Components to Build:**
1. **DoclingProcessor** - Unified document processing for PDF/DOCX/Images using Docling
2. **DocumentStructureAnalyzer** - Extract and analyze document structure from Docling output
3. **ContentExtractor** - Clean text and metadata extraction from Docling results
4. **ContentValidator** - Ensure parsing quality and completeness

---

### **Phase 2: RAG Processing Pipeline**
```
Parsed Content → Semantic Chunker → Embeddings → Vector Storage → RAG Ready
```

**Core Components:**
1. **SemanticChunker** - Intelligent text splitting
2. **EmbeddingService** - Generate vector embeddings  
3. **ChromaRepository** - Vector storage operations
4. **ChunkValidator** - Quality assurance

---

### **Phase 3: Structured Extraction Pipeline**
```
Parsed Content → Field Discovery → Agent Swarm → Data Extraction → Structured Storage
```

**Core Components:**
1. **FieldDiscoveryAgent** - Auto-detect extractable fields
2. **AgentScalingManager** - Dynamic agent allocation
3. **ExtractionAgent** - Structured data extraction
4. **DataValidator** - Extracted data quality

---

## 🏗️ **Pipeline Architecture**

### **Phase 1: Document Processing Components**
```python
src/backend/doc_processing_system/pipelines/
├── document_processing/
│   ├── __init__.py
│   ├── docling_processor.py          # Unified Docling-based document processing
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── structure_analyzer.py     # Extract structure from Docling output
│   │   ├── content_extractor.py      # Clean text/metadata extraction
│   │   └── content_validator.py      # Quality assurance
│   └── flows/
│       ├── __init__.py
│       └── document_processing_flow.py  # Main Prefect flow
```

### **Phase 2: RAG Pipeline Components**
```python
├── rag_processing/
│   ├── __init__.py
│   ├── semantic_chunker.py           # Intelligent chunking
│   ├── components/
│   │   ├── __init__.py
│   │   ├── embedding_service.py      # Vector generation
│   │   ├── chroma_repository.py      # Vector storage
│   │   └── chunk_validator.py        # Quality control
│   └── flows/
│       ├── __init__.py
│       └── rag_processing_flow.py    # RAG Prefect flow
```

### **Phase 3: Extraction Pipeline Components**
```python
├── structured_extraction/
│   ├── __init__.py
│   ├── field_discovery_agent.py      # Auto field detection
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── agent_scaling_manager.py  # Dynamic scaling
│   │   ├── extraction_agent.py       # Data extraction
│   │   └── data_validator.py         # Result validation
│   └── flows/
│       ├── __init__.py
│       └── extraction_flow.py        # Extraction Prefect flow
```

### **Orchestration Layer**
```python
└── orchestration/
    ├── __init__.py
    ├── main_flow.py                  # Master orchestrator
    ├── flow_coordinator.py           # Inter-pipeline coordination
    └── deployment/
        ├── __init__.py
        └── flow_deployments.py       # Prefect deployment configs
```

---

## 🚀 **Prefect Flow Architecture**

### **Main Orchestrator Flow:**
```python
@flow(name="document-processing-master")
def process_document(document_id: str, file_path: str):
    # Phase 1: Document Processing
    parsed_content = document_processing_flow(document_id, file_path)
    
    # Phase 2 & 3: Parallel Processing
    rag_future = rag_processing_flow.submit(document_id, parsed_content)
    extraction_future = extraction_flow.submit(document_id, parsed_content)
    
    # Wait for completion
    rag_result = rag_future.result()
    extraction_result = extraction_future.result()
    
    return {
        "document_id": document_id,
        "rag_result": rag_result,
        "extraction_result": extraction_result
    }
```

### **Individual Pipeline Flows:**
```python
@flow(name="document-processing")
def document_processing_flow(document_id: str, file_path: str):
    # Tasks for parsing, extraction, validation
    pass

@flow(name="rag-processing") 
def rag_processing_flow(document_id: str, content: str):
    # Tasks for chunking, embedding, storage
    pass

@flow(name="structured-extraction")
def extraction_flow(document_id: str, content: str):
    # Tasks for field discovery, agent processing
    pass
```

---

## 📊 **Success Metrics Per Phase**

### **Phase 1 Complete When:**
- ✅ Upload PDF → Get clean parsed text + structure via Docling
- ✅ Upload DOCX → Get clean parsed text + structure via Docling  
- ✅ Upload Image → Get OCR text + structure via Docling
- ✅ Unified document processing Prefect flow working
- ✅ All document types processed through single Docling pipeline

### **Phase 2 Complete When:**
- ✅ Parsed content → Semantic chunks created
- ✅ Chunks → Vector embeddings generated
- ✅ Embeddings → Stored in ChromaDB
- ✅ RAG processing Prefect flow working

### **Phase 3 Complete When:**
- ✅ Document → Auto-discovered extractable fields
- ✅ Fields → Agent swarm processes document
- ✅ Extraction → Structured data in database
- ✅ Extraction Prefect flow working

---

## 🎯 **Implementation Strategy**

1. **Build Pipeline Structure** → Create pipelines/ directory with proper organization
2. **Implement Phase 1** → Document processing components and Prefect flow
3. **Implement Phase 2** → RAG pipeline components and Prefect flow
4. **Implement Phase 3** → Extraction pipeline components and Prefect flow
5. **Orchestrate** → Master flow to coordinate all pipelines
6. **Deploy** → Prefect deployment configurations

**Focus:** Build robust, testable pipeline components with clear separation of concerns and comprehensive Prefect flow orchestration.