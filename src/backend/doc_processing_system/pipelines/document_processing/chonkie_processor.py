"""
ChonkieProcessor - Complete replacement for DoclingProcessor using unified Chonkie pipeline.
Integrates document processing + chunking + embeddings + Weaviate storage in a single pipeline.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from chonkie import SentenceTransformerEmbeddings, OpenAIEmbeddings, CohereEmbeddings
from chonkie import WeaviateHandshake
from chonkie import TextChef

from .chonkie_two_stage_chunker import ChonkieTwoStageChunker
from ...data_models.document import ParsedDocument, DocumentMetadata, FileType


class ChonkieProcessor:
    """Complete replacement for DoclingProcessor using Chonkie pipeline."""
    
    def __init__(self, 
                 enable_vision: bool = True,
                 embedding_model: str = "BAAI/bge-large-en-v1.5",
                 chunk_size: int = 700,
                 semantic_threshold: float = 0.75,
                 concurrent_agents: int = 10,
                 chunking_model: str = "gemini-2.0-flash",
                 weaviate_collection: str = "rag_documents",
                 weaviate_url: str = None,
                 weaviate_api_key: str = None):
        """Initialize ChonkieProcessor with unified pipeline.
        
        Args:
            enable_vision: Enable vision processing (for compatibility)
            embedding_model: Embedding model (supports multiple providers)
            chunk_size: Target chunk size for chunking
            semantic_threshold: Similarity threshold for semantic splits
            concurrent_agents: Number of concurrent boundary agents
            chunking_model: LLM model for boundary decisions
            weaviate_collection: Weaviate collection name
            weaviate_url: Weaviate server URL
            weaviate_api_key: Weaviate API key
        """
        self.enable_vision = enable_vision
        self.embedding_model = embedding_model
        self.weaviate_collection = weaviate_collection
        
        # Initialize output manager for compatibility (lazy loaded)
        self.output_manager = None
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Configure embeddings based on model type
        self.embeddings = self._initialize_embeddings(embedding_model)
        
        # Initialize our custom two-stage chunker
        self.chunker = ChonkieTwoStageChunker(
            chunk_size=chunk_size,
            semantic_threshold=semantic_threshold,
            boundary_context=200,  # Fixed boundary context
            concurrent_agents=concurrent_agents,
            model_name=chunking_model
        )
        
        # Configure Weaviate handshake for direct storage
        self.weaviate_handshake = WeaviateHandshake(
            embeddings=self.embeddings,
            collection_name=weaviate_collection,
            url=weaviate_url or os.getenv("WEAVIATE_URL", "http://localhost:8080"),
            api_key=weaviate_api_key or os.getenv("WEAVIATE_API_KEY")
        )
        
        # Initialize complete Chonkie TextChef (pipeline orchestrator)
        self.chef = TextChef(
            chunker=self.chunker,
            embeddings=self.embeddings,
            handshake=self.weaviate_handshake
        )
        
        self.logger.info("ChonkieProcessor initialized - complete DoclingProcessor replacement")
        self.logger.info(f"Configuration: embedding_model={embedding_model}, collection={weaviate_collection}")
    
    def _initialize_embeddings(self, embedding_model: str):
        """Initialize appropriate embeddings provider based on model string."""
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
    
    async def process_document_with_duplicate_check(self, raw_file_path: str, user_id: str = "default") -> Dict[str, Any]:
        """Complete workflow: check duplicates, process with Chonkie, save results.
        
        This method maintains exact compatibility with DoclingProcessor interface.
        
        Args:
            raw_file_path: Path to the raw document file
            user_id: User who uploaded the document
            
        Returns:
            Dict containing processing results and message data
        """
        try:
            # Step 1: Check for duplicates using existing output manager
            output_manager = self._get_output_manager()
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
                "processing_method": "chonkie_unified"
            }
            
            save_result = output_manager.save_processed_document(
                document_id, parsed_document.content, metadata, user_id
            )
            
            if save_result["status"] == "error":
                return save_result
            
            # Step 4: Prepare Kafka message
            message_result = output_manager.prepare_kafka_message(
                document_id, save_result["processed_file_path"], metadata, user_id
            )
            
            # Step 5: Combine all results with Chonkie stats
            complete_result = {
                "status": "completed",
                "document_id": document_id,
                "processed_file_path": save_result["processed_file_path"],
                "document_directory": save_result["document_directory"],
                "kafka_message": message_result.get("kafka_message"),
                "parsed_document": parsed_document,
                "message": f"Document processed with Chonkie: {document_id}",
                "chonkie_stats": getattr(parsed_document, '_chonkie_stats', {})
            }
            
            self.logger.info(f"Complete Chonkie processing workflow finished: {document_id}")
            return complete_result
            
        except Exception as e:
            self.logger.error(f"Chonkie processing workflow failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Chonkie processing failed: {e}"
            }
    
    async def process_document_with_vision(self, file_path: str, document_id: str, user_id: str = "default") -> ParsedDocument:
        """Process document with Chonkie pipeline + vision integration.
        
        This method maintains exact compatibility with DoclingProcessor interface.
        
        Args:
            file_path: Path to the document file
            document_id: Unique document identifier
            user_id: User who uploaded the document
            
        Returns:
            ParsedDocument: Document with Chonkie processing metadata
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        self.logger.info(f"Processing document with Chonkie: {file_path_obj.name}")
        
        # Read document content
        with open(file_path_obj, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Process through complete Chonkie pipeline
        # This handles: chunking → embeddings → Weaviate storage
        pipeline_result = await self._run_chonkie_pipeline(content, document_id)
        
        # Create ParsedDocument for compatibility
        file_stats = file_path_obj.stat()
        metadata = DocumentMetadata(
            document_id=document_id,
            file_type=self._get_file_type(file_path_obj).value,
            file_size=file_stats.st_size,
            upload_timestamp=datetime.now(),
            user_id=user_id
        )
        
        # Create ParsedDocument with original content
        # (chunks and embeddings are stored in Weaviate)
        parsed_doc = ParsedDocument(
            document_id=document_id,
            content=content,
            page_count=1,  # Simplified for now - can be enhanced later
            metadata=metadata
        )
        
        # Add Chonkie processing metadata
        parsed_doc._chonkie_stats = pipeline_result
        
        return parsed_doc
    
    async def _run_chonkie_pipeline(self, content: str, document_id: str) -> Dict[str, Any]:
        """Run the complete Chonkie pipeline: chunking → embeddings → storage."""
        try:
            # Use Chonkie TextChef to process the complete pipeline
            result = await self.chef.cook_async(
                text=content,
                document_id=document_id
            )
            
            # Extract metrics
            chunks_processed = len(result.chunks) if hasattr(result, 'chunks') else 0
            embeddings_generated = len(result.embeddings) if hasattr(result, 'embeddings') else 0
            
            # Get storage result from handshake
            storage_result = result.handshake_result if hasattr(result, 'handshake_result') else {}
            vectors_stored = storage_result.get("stored_count", 0)
            
            processing_stats = {
                "chunks_processed": chunks_processed,
                "embeddings_generated": embeddings_generated,
                "vectors_stored": vectors_stored,
                "processing_time": getattr(result, 'processing_time', 0),
                "embedding_model": self.embedding_model,
                "chunking_strategy": "two_stage_semantic_boundary",
                "weaviate_collection": self.weaviate_collection
            }
            
            self.logger.info(f"Chonkie pipeline complete: {chunks_processed} chunks → {embeddings_generated} embeddings → {vectors_stored} vectors")
            
            return processing_stats
            
        except Exception as e:
            self.logger.error(f"Chonkie pipeline failed: {e}")
            raise RuntimeError(f"Chonkie pipeline processing failed: {e}")
    
    def _get_output_manager(self):
        """Lazy initialization of DocumentOutputManager to avoid circular imports."""
        if self.output_manager is None:
            from .utils.document_output_manager import DocumentOutputManager
            self.output_manager = DocumentOutputManager()
        return self.output_manager
    
    def _get_file_type(self, file_path: Path) -> FileType:
        """Determine file type from file extension."""
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
            # Default to PDF for unsupported types
            return FileType.PDF
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for Chonkie processor."""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger