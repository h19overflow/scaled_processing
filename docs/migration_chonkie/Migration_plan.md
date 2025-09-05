Current Architecture Analysis

  Current Complex Pipeline:
  1. DoclingProcessor → Document parsing + vision processing
  2. RAG Flow → 5 separate Prefect tasks (chunking, boundary refinement, formatting, embeddings, storage)
  3. WeaviateIngestionEngine → Separate ingestion layer (334 lines)
  4. Multiple Task Files → Each stage has separate task implementations

  Target Chonkie Architecture:
  1. ChonkieProcessor → Unified document processing + chunking + embeddings + storage
  2. Direct Weaviate Integration → Native Chonkie → Weaviate handshake
  3. Embedded Vision Processing → Chonkie VLM integration

  Migration Strategy: Unified Replacement

  Phase 1: Chonkie Core Integration (Week 1)

  Step 1.1: Install Chonkie with Full Dependencies
  pip install chonkie[all]  # Includes all embeddings providers
  pip install chonkie[weaviate]  # Weaviate handshake integration

  Step 1.2: Create Unified ChonkieProcessor
  # File: src/backend/doc_processing_system/pipelines/document_processing/chonkie_processor.py

  from chonkie import Pipeline, SentenceTransformerEmbeddings
  from chonkie.embeddings import OpenAIEmbeddings, CohereEmbeddings
  from chonkie.handshakes.weaviate import WeaviateHandshake
  from chonkie.chunkers import SemanticChunker, SentenceChunker
  from chonkie.refinery import TokenRefinery, MergeRefinery

  class ChonkieProcessor:
      """Unified document processor replacing DoclingProcessor + RAG Flow"""

      def __init__(self,
                   embedding_model: str = "BAAI/bge-large-en-v1.5",
                   chunking_strategy: str = "semantic",
                   enable_vision: bool = True,
                   weaviate_config: dict = None):

          # Initialize Chonkie pipeline components
          self.embeddings = SentenceTransformerEmbeddings(model_name=embedding_model)

          # Configure chunker based on strategy
          if chunking_strategy == "semantic":
              self.chunker = SemanticChunker(
                  embedding_model=self.embeddings,
                  similarity_threshold=0.75
              )
          else:
              self.chunker = SentenceChunker(chunk_size=700)

          # Setup Weaviate handshake for direct storage
          self.weaviate_handshake = WeaviateHandshake(
              embeddings=self.embeddings,
              **weaviate_config
          )

          # Complete pipeline
          self.pipeline = Pipeline([
              self.chunker,
              TokenRefinery(max_tokens=512),
              MergeRefinery(min_chunk_size=100),
              self.embeddings,
              self.weaviate_handshake
          ])

      async def process_document_complete(self, file_path: str, document_id: str) -> Dict[str, Any]:
          """Single method replacing entire DoclingProcessor + RAG Flow"""
          # Process document through complete pipeline
          result = await self.pipeline.process(file_path)

          return {
              "status": "success",
              "document_id": document_id,
              "chunks_processed": result.chunk_count,
              "embeddings_generated": result.embedding_count,
              "vectors_stored": result.weaviate_count,
              "processing_time": result.total_time
          }

  Phase 2: Interface Compatibility Layer (Week 1-2)

  Step 2.1: Maintain DoclingProcessor Interface
  # Modify existing docling_processor.py
  class DoclingProcessor:
      def __init__(self, enable_vision: bool = True, use_chonkie: bool = False):
          if use_chonkie:
              self.chonkie_processor = ChonkieProcessor(
                  enable_vision=enable_vision,
                  embedding_model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
              )
          else:
              # Keep existing Docling logic
              self._initialize_docling()

      async def process_document_with_duplicate_check(self, raw_file_path: str, user_id: str = "default") -> Dict[str, Any]:
          if hasattr(self, 'chonkie_processor'):
              # Use Chonkie unified pipeline
              return await self.chonkie_processor.process_document_complete(raw_file_path, document_id)
          else:
              # Existing Docling logic
              return await self._process_with_docling()

  Step 2.2: Maintain RAG Flow Interface
  # Modify existing rag_processing_flow.py
  @flow(name="rag_processing_pipeline")
  async def rag_processing_flow(
      file_path: str,
      document_id: str,
      use_chonkie_pipeline: bool = False,  # Feature flag
      embedding_model: str = "BAAI/bge-large-en-v1.5",
      **kwargs
  ) -> Dict[str, Any]:

      if use_chonkie_pipeline:
          # Single Chonkie task replaces all 5 stages
          logger.info("🚀 Using Chonkie unified pipeline")
          result = await chonkie_unified_task(
              file_path=file_path,
              document_id=document_id,
              embedding_model=embedding_model,
              **kwargs
          )

          # Convert to existing interface format
          return {
              "pipeline_status": "success",
              "document_id": document_id,
              "stages": {
                  "chunking": {"status": "success", "chunk_count": result["chunks_processed"]},
                  "embeddings": {"status": "success", "embeddings_count": result["embeddings_generated"]},
                  "storage": {"status": "success", "vectors_stored": result["vectors_stored"]}
              }
          }
      else:
          # Existing 5-stage pipeline
          return await _run_traditional_pipeline()

  Phase 3: Weaviate Integration Replacement (Week 2)

  Step 3.1: Replace WeaviateIngestionEngine
  - Chonkie's WeaviateHandshake replaces entire weaviate_ingestion_engine.py (334 lines → ~50 lines)
  - Direct pipeline integration eliminates separate ingestion step
  - Built-in batching and error handling

  Step 3.2: Unified Task Implementation
  # File: flows/tasks/chonkie_tasks.py
  from chonkie import Pipeline

  @task(name="chonkie_unified_task", retries=2, timeout_seconds=1800)
  async def chonkie_unified_task(
      file_path: str,
      document_id: str,
      embedding_model: str = "BAAI/bge-large-en-v1.5",
      collection_name: str = "rag_documents",
      **kwargs
  ) -> Dict[str, Any]:
      """Single task replacing semantic_chunking + boundary_refinement + formatting + embeddings + storage"""

      # Initialize Chonkie processor
      processor = ChonkieProcessor(
          embedding_model=embedding_model,
          weaviate_config={"collection_name": collection_name}
      )

      # Process through complete pipeline
      result = await processor.process_document_complete(file_path, document_id)

      return {
          "task_status": "success",
          "chunks_processed": result["chunks_processed"],
          "embeddings_generated": result["embeddings_generated"],
          "vectors_stored": result["vectors_stored"],
          "task_processing_time": result["processing_time"]
      }

  Phase 4: Advanced Features & Optimization (Week 3)

  Step 4.1: Multiple Embedding Models Support
  class ChonkieProcessor:
      def __init__(self, embedding_model: str = "BAAI/bge-large-en-v1.5"):
          # Support multiple embedding providers
          if embedding_model.startswith("openai:"):
              self.embeddings = OpenAIEmbeddings(model=embedding_model.split(":")[1])
          elif embedding_model.startswith("cohere:"):
              self.embeddings = CohereEmbeddings(model=embedding_model.split(":")[1])
          else:
              # Default to Hugging Face sentence-transformers
              self.embeddings = SentenceTransformerEmbeddings(model_name=embedding_model)

  Step 4.2: VLM Integration with Chonkie
  # Enhanced vision processing through Chonkie VLM
  from chonkie.vision import VLMProcessor

  class ChonkieProcessor:
      def __init__(self, enable_vision: bool = True):
          if enable_vision:
              self.vlm_processor = VLMProcessor()
              self.pipeline.add_step(self.vlm_processor)

  Phase 5: Code Elimination & Cleanup (Week 4)

  Files to be ELIMINATED (Significant Code Reduction):
  1. weaviate_ingestion_engine.py (334 lines) → Replaced by Chonkie WeaviateHandshake
  2. flows/tasks/semantic_chunking_task.py → Replaced by Chonkie chunkers
  3. flows/tasks/boundary_refinement_task.py → Replaced by Chonkie refineries
  4. flows/tasks/chunk_formatting_task.py → Built into Chonkie pipeline
  5. flows/tasks/generate_embeddings_task.py → Replaced by Chonkie embeddings
  6. flows/tasks/store_vectors_task.py → Replaced by WeaviateHandshake

  Estimated Code Reduction: ~1,500+ lines eliminated

  Phase 6: Configuration & Migration (Week 4)

  Environment Configuration:
  # Feature flags for controlled migration
  CHONKIE_ENABLED=true
  CHONKIE_EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
  CHONKIE_CHUNKING_STRATEGY=semantic
  CHONKIE_WEAVIATE_DIRECT=true
  CHONKIE_VLM_ENABLED=true

  # Alternative embedding models
  # CHONKIE_EMBEDDING_MODEL=openai:text-embedding-3-large
  # CHONKIE_EMBEDDING_MODEL=cohere:embed-english-v3.0
  # CHONKIE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

  Migration Strategy:
  1. Week 1: Deploy with CHONKIE_ENABLED=false (no changes)
  2. Week 2: Enable for test documents only
  3. Week 3: A/B test with 50/50 split
  4. Week 4: Full migration + code cleanup

  Expected Benefits

  Performance Improvements:
  - 2-33x faster processing (documented Chonkie performance)
  - Single pipeline instead of 5-stage Prefect flow
  - Direct Weaviate integration eliminates intermediate storage
  - Native embeddings without separate processing step

  Code Simplification:
  - ~1,500 lines eliminated from task files and ingestion engine
  - Single configuration for entire pipeline
  - Unified error handling through Chonkie
  - Built-in batching and optimization

  Feature Enhancements:
  - Multiple embedding providers (OpenAI, Cohere, Hugging Face, etc.)
  - Advanced VLM processing for images/tables
  - Smart chunking strategies (semantic, sentence, custom)
  - Direct Weaviate handshake with optimized batching

  Risk Mitigation

  Backward Compatibility:
  - All existing interfaces preserved
  - Feature flags for instant rollback
  - Gradual migration with A/B testing
  - Fallback to existing pipeline

  Validation Strategy:
  - Compare chunk quality between old/new pipelines
  - Validate embedding generation accuracy
  - Test Weaviate storage consistency
  - Performance benchmarking
