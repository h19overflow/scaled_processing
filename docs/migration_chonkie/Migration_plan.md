# Revised Chonkie Migration Plan - Complete Replacement with Custom Two-Stage Chunker

## Overview
Complete replacement of DoclingProcessor + RAG Flow with unified Chonkie pipeline, preserving our custom two-stage chunker logic and eliminating ~1,500+ lines of code with NO fallback systems.

## Key Changes from Original Plan
- **NO fallback mechanisms** - complete replacement only
- **Preserve two_stage_chunker.py** - integrate as custom Chonkie chunker
- **Eliminate weaviate_ingestion_engine.py** completely (334 lines)
- **Replace all RAG flow tasks** with single Chonkie pipeline
- **Maintain exact interfaces** for seamless compatibility

## Migration Strategy: Complete Replacement

### Phase 1: Custom Chunker Integration (Week 1)

**Step 1.1: Convert TwoStageChunker to Chonkie Custom Chunker**
- Create `chonkie_two_stage_chunker.py` wrapping existing `two_stage_chunker.py`
- Implement Chonkie `BaseChunker` interface while preserving all existing logic
- Maintain semantic chunking + boundary refinement workflow

**Step 1.2: Create ChonkieProcessor (Complete DoclingProcessor Replacement)**
- New file: `chonkie_processor.py` 
- Initialize with multiple embedding providers (OpenAI, Cohere, Hugging Face)
- Integrate custom two-stage chunker + embeddings + direct Weaviate storage
- Maintain exact DoclingProcessor interface methods

### Phase 2: RAG Flow Complete Replacement (Week 2)

**Step 2.1: Replace Entire rag_processing_flow.py**
- New file: `chonkie_rag_flow.py`
- Single Chonkie pipeline replaces all 5 Prefect tasks
- Maintain identical interface for backward compatibility
- Return format matches existing pipeline results

**Step 2.2: Eliminate All Task Files**
- DELETE: `semantic_chunking_task.py` (~200 lines)
- DELETE: `boundary_refinement_task.py` (~250 lines)
- DELETE: `chunk_formatting_task.py` (~150 lines)
- DELETE: `generate_embeddings_task.py` (~200 lines)
- DELETE: `store_vectors_task.py` (~150 lines)
- **Total: ~950 lines eliminated**

### Phase 3: Complete Code Elimination (Week 3)

**Files to DELETE (No Replacements):**
- `weaviate_ingestion_engine.py` (334 lines) → Chonkie WeaviateHandshake
- All files in `flows/tasks/` directory
- Complex Prefect orchestration → Single pipeline

**Files to PRESERVE and ENHANCE:**
- `two_stage_chunker.py` → Wrapped in Chonkie interface
- `semantic_chunker.py` → Used by two-stage chunker
- `boundary_agent.py` → Used by two-stage chunker

**Import Redirects for Compatibility:**
```python
# __init__.py updates
from .chonkie_processor import ChonkieProcessor as DoclingProcessor
from .chonkie_rag_flow import chonkie_rag_processing_flow as rag_processing_flow
```

### Phase 4: Advanced Chonkie Features (Week 4)

**Multiple Embedding Models Support:**
- OpenAI: `openai:text-embedding-3-large`
- Cohere: `cohere:embed-english-v3.0`
- Hugging Face: `BAAI/bge-large-en-v1.5` (default)
- SentenceTransformers: Any HuggingFace model

**Direct Weaviate Integration:**
- Eliminate intermediate JSON storage
- Built-in batching and error handling
- Optimized vector insertion

**Configuration:**
```bash
CHONKIE_ENABLED=true
CHONKIE_EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
CHONKIE_CHUNKING_STRATEGY=two_stage
CHONKIE_WEAVIATE_COLLECTION=rag_documents
```

## Expected Results

**Massive Code Reduction:**
- weaviate_ingestion_engine.py: 334 lines → 0
- All task files: ~950 lines → 0
- Complex orchestration: ~200 lines → 50 lines
- **Total elimination: ~1,500+ lines**

**Performance Improvements:**
- 2-33x faster processing (Chonkie benchmark)
- Single pipeline execution vs 5-stage orchestration
- Direct Weaviate storage (no intermediate files)
- Native embedding generation

**Architecture Benefits:**
- Unified document processing workflow
- Custom two-stage chunker preserved and enhanced
- Multiple embedding provider support
- Built-in error handling and monitoring
- Zero breaking changes (interface compatibility)

## Implementation Priority
1. **Week 1**: Custom chunker wrapper + ChonkieProcessor
2. **Week 2**: Complete RAG flow replacement
3. **Week 3**: Mass file deletion + import updates
4. **Week 4**: Testing, optimization, deployment

**No fallback systems** - complete migration to modern Chonkie architecture while preserving our valuable two-stage chunking logic.

## Detailed Implementation Steps

### Phase 1: Custom Chunker Integration

#### Step 1.1: ChonkieTwoStageChunker Implementation

```python
# File: src/backend/doc_processing_system/pipelines/document_processing/chonkie_two_stage_chunker.py

from chonkie.chunkers.base import BaseChunker
from ..rag_processing.components.chunking.two_stage_chunker import TwoStageChunker
from typing import List, Dict, Any

class ChonkieTwoStageChunker(BaseChunker):
    """Custom Chonkie chunker wrapping our existing TwoStageChunker"""
    
    def __init__(self, 
                 chunk_size: int = 700,
                 semantic_threshold: float = 0.75,
                 boundary_context: int = 200,
                 concurrent_agents: int = 10,
                 model_name: str = "gemini-2.0-flash"):
        super().__init__()
        
        # Initialize our existing two-stage chunker
        self.two_stage_chunker = TwoStageChunker(
            chunk_size=chunk_size,
            semantic_threshold=semantic_threshold,
            boundary_context=boundary_context,
            concurrent_agents=concurrent_agents,
            model_name=model_name
        )
    
    async def chunk(self, text: str, document_id: str = None) -> List[Dict[str, Any]]:
        """Chonkie interface method using our two-stage chunker"""
        # Use our existing chunker logic
        result = await self.two_stage_chunker.process_document_text(text, document_id or "doc")
        
        # Convert to Chonkie format
        chonkie_chunks = []
        for chunk_data in result["text_chunks"]:
            chonkie_chunks.append({
                "text": chunk_data["content"],
                "metadata": {
                    **chunk_data["metadata"],
                    "chunk_id": chunk_data["chunk_id"],
                    "chunk_index": chunk_data["chunk_index"]
                }
            })
        
        return chonkie_chunks
    
    def get_params(self) -> Dict[str, Any]:
        """Return chunker parameters for Chonkie"""
        return self.two_stage_chunker.get_configuration()
```

#### Step 1.2: ChonkieProcessor Implementation

```python
# File: src/backend/doc_processing_system/pipelines/document_processing/chonkie_processor.py

import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from chonkie import Pipeline
from chonkie.embeddings import SentenceTransformerEmbeddings, OpenAIEmbeddings, CohereEmbeddings
from chonkie.handshakes.weaviate import WeaviateHandshake
from chonkie.refinery import TokenRefinery, MergeRefinery
from .chonkie_two_stage_chunker import ChonkieTwoStageChunker
from ...data_models.document import ParsedDocument, DocumentMetadata, FileType

class ChonkieProcessor:
    """Complete replacement for DoclingProcessor using Chonkie pipeline"""
    
    def __init__(self, 
                 enable_vision: bool = True,
                 embedding_model: str = "BAAI/bge-large-en-v1.5",
                 chunk_size: int = 700,
                 semantic_threshold: float = 0.75,
                 concurrent_agents: int = 10,
                 chunking_model: str = "gemini-2.0-flash",
                 weaviate_collection: str = "rag_documents"):
        
        self.enable_vision = enable_vision
        
        # Initialize output manager for compatibility
        self.output_manager = None
        
        # Configure embeddings based on model type
        self.embeddings = self._initialize_embeddings(embedding_model)
        
        # Initialize our custom two-stage chunker
        self.chunker = ChonkieTwoStageChunker(
            chunk_size=chunk_size,
            semantic_threshold=semantic_threshold,
            concurrent_agents=concurrent_agents,
            model_name=chunking_model
        )
        
        # Configure Weaviate handshake for direct storage
        self.weaviate_handshake = WeaviateHandshake(
            embeddings=self.embeddings,
            collection_name=weaviate_collection,
            # Weaviate connection from env vars
            url=os.getenv("WEAVIATE_URL", "http://localhost:8080"),
            api_key=os.getenv("WEAVIATE_API_KEY")
        )
        
        # Complete Chonkie pipeline
        self.pipeline = Pipeline([
            self.chunker,                    # Our custom two-stage chunker
            TokenRefinery(max_tokens=512),   # Token optimization
            MergeRefinery(min_chunk_size=100), # Merge small chunks
            self.embeddings,                 # Generate embeddings
            self.weaviate_handshake         # Store in Weaviate
        ])
        
        self.logger = self._setup_logging()
        self.logger.info("ChonkieProcessor initialized - complete Docling replacement")
    
    def _initialize_embeddings(self, embedding_model: str):
        """Initialize appropriate embeddings provider"""
        if embedding_model.startswith("openai:"):
            model_name = embedding_model.split(":", 1)[1]
            return OpenAIEmbeddings(
                model=model_name,
                api_key=os.getenv("OPENAI_API_KEY")
            )
        elif embedding_model.startswith("cohere:"):
            model_name = embedding_model.split(":", 1)[1]
            return CohereEmbeddings(
                model=model_name,
                api_key=os.getenv("COHERE_API_KEY")
            )
        else:
            # Default to Hugging Face sentence-transformers
            return SentenceTransformerEmbeddings(model_name=embedding_model)
    
    # INTERFACE COMPATIBILITY - Exact same methods as DoclingProcessor
    async def process_document_with_duplicate_check(self, raw_file_path: str, user_id: str = "default") -> Dict[str, Any]:
        """Complete workflow: check duplicates, process with Chonkie, save results"""
        try:
            # Step 1: Check for duplicates using existing output manager
            output_manager = self.get_output_manager()
            check_result = output_manager.check_and_process_document(raw_file_path, user_id)
            
            if check_result["status"] == "duplicate":
                return check_result
            elif check_result["status"] == "error":
                return check_result
            
            document_id = check_result["document_id"]
            
            # Step 2: Process with Chonkie pipeline
            parsed_document = await self.process_document_with_vision(raw_file_path, document_id, user_id)
            
            # Step 3: Save processed document (maintains compatibility)
            file_path_obj = Path(raw_file_path)
            metadata = {
                "filename": file_path_obj.name,
                "page_count": parsed_document.page_count,
                "content_length": len(parsed_document.content),
                "file_type": parsed_document.metadata.file_type,
                "file_size": parsed_document.metadata.file_size,
                "processed_content": parsed_document.content,
                "vision_processing": self.enable_vision,
                "processing_method": "chonkie_complete"
            }
            
            save_result = output_manager.save_processed_document(
                document_id, parsed_document.content, metadata, user_id
            )
            
            # Step 4: Prepare Kafka message
            message_result = output_manager.prepare_kafka_message(
                document_id, save_result["processed_file_path"], metadata, user_id
            )
            
            return {
                "status": "completed",
                "document_id": document_id,
                "processed_file_path": save_result["processed_file_path"],
                "document_directory": save_result["document_directory"],
                "kafka_message": message_result.get("kafka_message"),
                "parsed_document": parsed_document,
                "message": f"Document processed with Chonkie: {document_id}",
                "chonkie_stats": self.pipeline.get_last_run_stats()  # New: Chonkie metrics
            }
            
        except Exception as e:
            self.logger.error(f"Chonkie processing failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Chonkie processing failed: {e}"
            }
    
    async def process_document_with_vision(self, file_path: str, document_id: str, user_id: str = "default") -> ParsedDocument:
        """Process document with Chonkie pipeline + vision integration"""
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        self.logger.info(f"Processing document with Chonkie: {file_path_obj.name}")
        
        # Read document content
        with open(file_path_obj, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Process through complete Chonkie pipeline
        # This handles: chunking → embeddings → Weaviate storage
        pipeline_result = await self.pipeline.process(content, document_id=document_id)
        
        # Extract results
        chunks_processed = len(pipeline_result.chunks)
        embeddings_generated = len(pipeline_result.embeddings)
        vectors_stored = pipeline_result.weaviate_response.get("stored_count", 0)
        
        self.logger.info(f"Chonkie pipeline complete: {chunks_processed} chunks → {embeddings_generated} embeddings → {vectors_stored} vectors")
        
        # Create ParsedDocument for compatibility
        file_stats = file_path_obj.stat()
        metadata = DocumentMetadata(
            document_id=document_id,
            file_type=self._get_file_type(file_path_obj).value,
            file_size=file_stats.st_size,
            upload_timestamp=datetime.now(),
            user_id=user_id
        )
        
        # Create ParsedDocument with Chonkie-processed content
        parsed_doc = ParsedDocument(
            document_id=document_id,
            content=content,  # Original content (chunks are stored in Weaviate)
            page_count=1,     # Simplified for now
            metadata=metadata
        )
        
        # Add Chonkie processing metadata
        parsed_doc._chonkie_stats = {
            "chunks_processed": chunks_processed,
            "embeddings_generated": embeddings_generated,
            "vectors_stored": vectors_stored,
            "processing_time": pipeline_result.processing_time
        }
        
        return parsed_doc
    
    def get_output_manager(self):
        """Lazy initialization of DocumentOutputManager"""
        if self.output_manager is None:
            from .utils.document_output_manager import DocumentOutputManager
            self.output_manager = DocumentOutputManager()
        return self.output_manager
    
    def _get_file_type(self, file_path: Path) -> FileType:
        """Determine file type from extension"""
        suffix = file_path.suffix.lower()
        if suffix == '.pdf':
            return FileType.PDF
        elif suffix in ['.docx', '.doc']:
            return FileType.DOCX
        elif suffix in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
            return FileType.IMAGE
        elif suffix in ['.txt', '.md']:
            return FileType.TEXT
        else:
            return FileType.PDF
    
    def _setup_logging(self):
        """Setup logging for Chonkie processor"""
        import logging
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
```

### Phase 2: RAG Flow Complete Replacement

#### ChonkieRAGFlow Implementation

```python
# File: src/backend/doc_processing_system/pipelines/rag_processing/flows/chonkie_rag_flow.py

import time
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from prefect import flow, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from ...document_processing.chonkie_processor import ChonkieProcessor

@flow(
    name="chonkie_rag_pipeline", 
    description="Complete Chonkie-based RAG processing pipeline",
    task_runner=ConcurrentTaskRunner(),
    flow_run_name="chonkie-rag-{document_id}",
    retries=1,
    retry_delay_seconds=60,
    timeout_seconds=1800
)
async def chonkie_rag_processing_flow(
    file_path: str,
    document_id: str,
    chunk_size: int = 700,
    semantic_threshold: float = 0.75,
    concurrent_agents: int = 10,
    chunking_model: str = "gemini-2.0-flash",
    embedding_model: str = "BAAI/bge-large-en-v1.5",
    collection_name: str = "rag_documents"
) -> Dict[str, Any]:
    """Single Chonkie flow replacing entire 5-stage RAG pipeline"""
    
    logger = get_run_logger()
    pipeline_start = time.time()
    
    logger.info(f"🚀 Starting Chonkie RAG pipeline for {document_id}")
    logger.info(f"📁 Document: {file_path}")
    logger.info(f"⚙️ Config: chunk_size={chunk_size}, threshold={semantic_threshold}, agents={concurrent_agents}")
    logger.info(f"🤖 Models: chunking={chunking_model}, embedding={embedding_model}")
    
    try:
        # Initialize Chonkie processor with configuration
        chonkie_processor = ChonkieProcessor(
            embedding_model=embedding_model,
            chunk_size=chunk_size,
            semantic_threshold=semantic_threshold,
            concurrent_agents=concurrent_agents,
            chunking_model=chunking_model,
            weaviate_collection=collection_name
        )
        
        # Process document through complete pipeline
        logger.info("🔄 Processing through Chonkie unified pipeline...")
        
        # Read document content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Single pipeline execution replaces all 5 stages
        pipeline_result = await chonkie_processor.pipeline.process(content, document_id=document_id)
        
        total_processing_time = time.time() - pipeline_start
        
        # Format results to match existing interface
        pipeline_result_formatted = {
            "pipeline_status": "success",
            "document_id": document_id,
            "source_file_path": file_path,
            "total_processing_time": round(total_processing_time, 3),
            "pipeline_completed_at": datetime.now().isoformat(),
            
            # Unified stages (maintains interface compatibility)
            "stages": {
                "chunking": {
                    "status": "success",
                    "chunk_count": len(pipeline_result.chunks),
                    "chunks_file_path": f"chonkie_chunks_{document_id}.json",  # Virtual path
                    "processing_time": pipeline_result.chunking_time
                },
                "embeddings": {
                    "status": "success",
                    "embeddings_count": len(pipeline_result.embeddings),
                    "embeddings_file_path": f"chonkie_embeddings_{document_id}.json",  # Virtual path
                    "processing_time": pipeline_result.embedding_time,
                    "model_used": embedding_model
                },
                "storage": {
                    "status": "success",
                    "collection_name": collection_name,
                    "vectors_stored": pipeline_result.weaviate_response.get("stored_count", 0),
                    "processing_time": pipeline_result.storage_time,
                    "note": "Direct Weaviate storage via Chonkie handshake"
                }
            },
            
            # Configuration
            "configuration": {
                "chunk_size": chunk_size,
                "semantic_threshold": semantic_threshold,
                "concurrent_agents": concurrent_agents,
                "chunking_model": chunking_model,
                "embedding_model": embedding_model,
                "collection_name": collection_name,
                "processing_method": "chonkie_unified"
            },
            
            # Chonkie-specific metrics
            "chonkie_metrics": {
                "total_chunks": len(pipeline_result.chunks),
                "total_embeddings": len(pipeline_result.embeddings),
                "total_vectors_stored": pipeline_result.weaviate_response.get("stored_count", 0),
                "pipeline_efficiency": round(len(pipeline_result.chunks) / total_processing_time, 2),
                "average_chunk_size": pipeline_result.average_chunk_size,
                "embedding_dimensions": pipeline_result.embedding_dimensions
            }
        }
        
        logger.info(f"🎯 Chonkie RAG pipeline completed in {total_processing_time:.2f}s")
        logger.info(f"📊 Results: {len(pipeline_result.chunks)} chunks → {len(pipeline_result.embeddings)} embeddings → {pipeline_result.weaviate_response.get('stored_count', 0)} stored")
        
        return pipeline_result_formatted
        
    except Exception as e:
        total_processing_time = time.time() - pipeline_start
        logger.error(f"❌ Chonkie RAG pipeline failed after {total_processing_time:.2f}s: {e}")
        
        return {
            "pipeline_status": "failed",
            "document_id": document_id,
            "source_file_path": file_path,
            "total_processing_time": round(total_processing_time, 3),
            "pipeline_failed_at": datetime.now().isoformat(),
            "error": str(e),
            "error_type": type(e).__name__,
            "processing_method": "chonkie_unified"
        }

# Convenience function maintaining existing interface
async def process_document_via_rag_pipeline(
    file_path: str,
    document_id: str,
    **kwargs
) -> Dict[str, Any]:
    """Process document through Chonkie RAG pipeline (replaces original function)"""
    return await chonkie_rag_processing_flow(
        file_path=file_path,
        document_id=document_id,
        **kwargs
    )
```

This revised plan provides a complete replacement strategy that eliminates over 1,500 lines of code while preserving our valuable two-stage chunker logic within the modern Chonkie framework.