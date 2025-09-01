"""
Two-Stage Chunker - Streamlined 2-stage chunking for RAG pipeline

Combines semantic chunking with agentic boundary refinement for optimal chunk boundaries.
Focused on chunk output for embeddings pipeline consumption.

Stage 1: Semantic chunking for initial context-aware splits
Stage 2: Agentic boundary review with merge/keep decisions
Output: Chunks saved to data/rag/chunks/ with metadata for Kafka messaging

Input: File path to processed markdown document (from upstream document processor)
Dependencies: All component modules (semantic_chunker, boundary_agent)
Integration: Main interface for RAG pipeline chunking via Kafka messaging
"""

import json
import logging
import asyncio
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from .semantic_chunker import SemanticChunker
from .boundary_agent import BoundaryReviewAgent


class TwoStageChunker:
    """Complete 2-stage chunking system with semantic analysis and boundary refinement."""
    
    def __init__(self, 
                 chunk_size: int = 700,
                 semantic_threshold: float = 0.75,
                 boundary_context: int = 200,
                 concurrent_agents: int = 10,
                 model_name: str = "gemini-2.0-flash"):
        """Initialize the 2-stage chunker.
        
        Args:
            chunk_size: Target chunk size for semantic chunking
            semantic_threshold: Similarity threshold for semantic splits
            boundary_context: Context window for boundary analysis
            concurrent_agents: Number of concurrent boundary review agents
            model_name: LLM model for boundary decisions
        """
        self.chunk_size = chunk_size
        self.semantic_threshold = semantic_threshold
        self.boundary_context = boundary_context
        self.concurrent_agents = concurrent_agents
        self.model_name = model_name
        
        # Set dedicated chunks directory for RAG pipeline
        self.chunks_directory = Path("data/rag/chunks")
        self.chunks_directory.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Initialize components (cached for performance)
        self._cached_semantic_chunker = SemanticChunker(
            chunk_size=chunk_size, 
            threshold=semantic_threshold
        )
        self._cached_boundary_agent = BoundaryReviewAgent(
            context_window=boundary_context,
            model_name=model_name
        )
        
        self.logger.info(f"🚀 2-Stage Chunker initialized (chunk_size={chunk_size}, threshold={semantic_threshold}, concurrent_agents={concurrent_agents}, model={model_name})")
    
    async def process_document(self, file_path: str, document_id: str) -> Dict[str, Any]:
        """Process document through complete 2-stage chunking pipeline.
        
        Args:
            file_path: Path to the document file to process
            document_id: Unique document identifier
            
        Returns:
            Dict containing chunk metadata for Kafka messaging
        """
        start_time = time.time()
        self.logger.info(f"🔄 Starting 2-stage chunking for {document_id} from {file_path}")
        
        # Read document content from file
        try:
            text = self._read_document_file(file_path)
            self.logger.info(f"📖 Document loaded: {len(text)} characters from {file_path}")
        except Exception as e:
            self.logger.error(f"❌ Failed to read document {file_path}: {e}")
            raise ValueError(f"Cannot read document file: {file_path}")
        
        # Stage 1: Semantic Chunking
        stage1_result = self._cached_semantic_chunker.chunk_text(text, document_id)
        initial_chunks = stage1_result["chunks"]
        
        self.logger.info(f"✅ Stage 1 complete: {len(initial_chunks)} semantic chunks")
        
        # Stage 2: Boundary Review and Refinement
        if len(initial_chunks) <= 1:
            # No boundaries to review
            final_chunks = initial_chunks
            stage2_result = {
                "boundary_decisions": [],
                "total_boundaries": 0,
                "merge_decisions": 0,
                "keep_decisions": 0,
                "error_decisions": 0,
                "processing_time_seconds": 0.0,
                "avg_confidence": 0.0
            }
        else:
            # Review boundaries and apply refinements with concurrent agents
            stage2_result = await self._cached_boundary_agent.review_all_boundaries(
                initial_chunks, max_concurrent=self.concurrent_agents
            )
            final_chunks = self._apply_boundary_decisions(initial_chunks, stage2_result["boundary_decisions"])
        
        total_processing_time = time.time() - start_time
        
        self.logger.info(f"✅ Stage 2 complete: {len(final_chunks)} refined chunks")
        self.logger.info(f"🎯 2-stage chunking complete: {len(initial_chunks)} → {len(final_chunks)} chunks in {total_processing_time:.3f}s")
        
        # Convert chunks to TextChunk models
        text_chunks = self._create_text_chunks(final_chunks, document_id)
        
        # Save chunks using TextChunk models
        chunks_path = self._save_text_chunks(text_chunks, document_id)
        
        return {
            "document_id": document_id,
            "source_file_path": file_path,
            "chunk_count": len(text_chunks),
            "chunks_file_path": str(chunks_path),
            "text_chunks": text_chunks,  # Return TextChunk dictionaries for direct use
            "processing_time_seconds": round(total_processing_time, 3),
            "original_length": len(text),
            "timestamp": datetime.now().isoformat(),
            "stage1_result": stage1_result,
            "stage2_result": stage2_result
        }
    
    def _read_document_file(self, file_path: str) -> str:
        """Read markdown document content from file.
        
        Args:
            file_path: Path to the markdown document file
            
        Returns:
            Document text content
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be read
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        try:
            # Read markdown content (set by upstream document processor)
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                raise ValueError(f"Document file is empty: {file_path}")
            
            self.logger.debug(f"📖 Read {len(content)} characters from {file_path}")
            return content
                
        except Exception as e:
            raise ValueError(f"Error reading markdown file {file_path}: {e}")
    
    async def process_document_text(self, text: str, document_id: str) -> Dict[str, Any]:
        """Process document from raw text (for backward compatibility and testing).
        
        Args:
            text: Document text content
            document_id: Unique document identifier
            
        Returns:
            Dict containing chunk metadata for Kafka messaging
        """
        start_time = time.time()
        self.logger.info(f"🔄 Starting 2-stage chunking for {document_id} from raw text")
        
        # Stage 1: Semantic Chunking
        stage1_result = self._cached_semantic_chunker.chunk_text(text, document_id)
        initial_chunks = stage1_result["chunks"]
        
        self.logger.info(f"✅ Stage 1 complete: {len(initial_chunks)} semantic chunks")
        
        # Stage 2: Boundary Review and Refinement
        if len(initial_chunks) <= 1:
            # No boundaries to review
            final_chunks = initial_chunks
            stage2_result = {
                "boundary_decisions": [],
                "total_boundaries": 0,
                "merge_decisions": 0,
                "keep_decisions": 0,
                "error_decisions": 0,
                "processing_time_seconds": 0.0,
                "avg_confidence": 0.0
            }
        else:
            # Review boundaries and apply refinements with concurrent agents
            stage2_result = await self._cached_boundary_agent.review_all_boundaries(
                initial_chunks, max_concurrent=self.concurrent_agents
            )
            final_chunks = self._apply_boundary_decisions(initial_chunks, stage2_result["boundary_decisions"])
        
        total_processing_time = time.time() - start_time
        
        self.logger.info(f"✅ Stage 2 complete: {len(final_chunks)} refined chunks")
        self.logger.info(f"🎯 2-stage chunking complete: {len(initial_chunks)} → {len(final_chunks)} chunks in {total_processing_time:.3f}s")
        
        # Convert chunks to TextChunk models
        text_chunks = self._create_text_chunks(final_chunks, document_id)
        
        # Save chunks using TextChunk models
        chunks_path = self._save_text_chunks(text_chunks, document_id)
        
        return {
            "document_id": document_id,
            "source_file_path": None,  # No file path for raw text input
            "chunk_count": len(text_chunks),
            "chunks_file_path": str(chunks_path),
            "text_chunks": text_chunks,  # Return TextChunk dictionaries for direct use
            "processing_time_seconds": round(total_processing_time, 3),
            "original_length": len(text),
            "timestamp": datetime.now().isoformat(),
            "stage1_result": stage1_result,
            "stage2_result": stage2_result
        }
    
    def _create_text_chunks(self, chunks: List[str], document_id: str) -> List[Dict[str, Any]]:
        """Convert string chunks to TextChunk model dictionaries.
        
        Args:
            chunks: List of chunk strings
            document_id: Document identifier
            
        Returns:
            List of TextChunk dictionaries
        """
        text_chunks = []
        
        for i, chunk_content in enumerate(chunks):
            # Generate deterministic chunk ID
            chunk_id = self._generate_chunk_id(document_id, i)
            
            # Create TextChunk dictionary matching the model
            text_chunk = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "content": chunk_content,
                "page_number": 0,  # Placeholder until page mapping is implemented
                "chunk_index": i,
                "metadata": {
                    "chunk_length": len(chunk_content),
                    "word_count": len(chunk_content.split()),
                    "created_at": datetime.now().isoformat(),
                    "chunking_strategy": "two_stage_semantic"
                }
            }
            
            text_chunks.append(text_chunk)
        
        return text_chunks
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate deterministic chunk ID.
        
        Args:
            document_id: Document identifier
            chunk_index: Index of chunk within document
            
        Returns:
            Unique chunk identifier
        """
        id_string = f"{document_id}_{chunk_index}"
        return hashlib.md5(id_string.encode()).hexdigest()[:16]
    
    def _save_text_chunks(self, text_chunks: List[Dict[str, Any]], document_id: str) -> Path:
        """Save TextChunk dictionaries to JSON file.
        
        Args:
            text_chunks: List of TextChunk dictionaries
            document_id: Document identifier
            
        Returns:
            Path to saved chunks file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chunks_{document_id}_{timestamp}.json"
        chunks_path = self.chunks_directory / filename
        
        try:
            chunks_data = {
                "document_id": document_id,
                "timestamp": datetime.now().isoformat(),
                "chunk_count": len(text_chunks),
                "chunks": text_chunks,  # List of TextChunk dictionaries
                "statistics": {
                    "total_characters": sum(chunk["metadata"]["chunk_length"] for chunk in text_chunks),
                    "total_words": sum(chunk["metadata"]["word_count"] for chunk in text_chunks),
                    "avg_chunk_length": round(sum(chunk["metadata"]["chunk_length"] for chunk in text_chunks) / len(text_chunks), 1) if text_chunks else 0,
                    "min_chunk_length": min(chunk["metadata"]["chunk_length"] for chunk in text_chunks) if text_chunks else 0,
                    "max_chunk_length": max(chunk["metadata"]["chunk_length"] for chunk in text_chunks) if text_chunks else 0
                }
            }
            
            with open(chunks_path, 'w', encoding='utf-8') as f:
                json.dump(chunks_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📄 TextChunk models saved: {chunks_path}")
            return chunks_path
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save TextChunk models: {e}")
            return chunks_path
    
    def _apply_boundary_decisions(self, chunks: List[str], decisions: List[Dict[str, Any]]) -> List[str]:
        """Apply boundary decisions to merge chunks where specified.
        
        Args:
            chunks: Original list of chunks
            decisions: List of boundary decisions
            
        Returns:
            List of chunks with merges applied
        """
        if not decisions:
            return chunks
        
        # Create merge map - which chunks to merge
        merge_map = {}
        for decision in decisions:
            if decision["decision"] == "MERGE":
                chunk_idx = decision["chunk_index"]
                merge_map[chunk_idx] = True
        
        refined_chunks = []
        i = 0
        
        while i < len(chunks):
            current_chunk = chunks[i]
            
            # Check if we should merge this chunk with the next one
            if i in merge_map and i + 1 < len(chunks):
                # Merge current chunk with next chunk
                merged_chunk = current_chunk + "\n\n" + chunks[i + 1]
                refined_chunks.append(merged_chunk)
                
                self.logger.debug(f"🔗 Merged chunks {i} and {i+1} (lengths: {len(current_chunk)} + {len(chunks[i + 1])} = {len(merged_chunk)})")
                
                i += 2  # Skip the next chunk since we merged it
            else:
                # Keep current chunk as is
                refined_chunks.append(current_chunk)
                i += 1
        
        return refined_chunks
    
    def _save_chunks(self, chunks: List[str], document_id: str) -> Path:
        """Save final chunks to JSON file.
        
        Args:
            chunks: Final processed chunks
            document_id: Document identifier
            
        Returns:
            Path to saved chunks file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chunks_{document_id}_{timestamp}.json"
        chunks_path = self.chunks_directory / filename
        
        try:
            chunks_data = {
                "document_id": document_id,
                "timestamp": datetime.now().isoformat(),
                "chunk_count": len(chunks),
                "chunks": [
                    {
                        "index": i,
                        "content": chunk,
                        "length": len(chunk),
                        "word_count": len(chunk.split())
                    }
                    for i, chunk in enumerate(chunks)
                ],
                "statistics": {
                    "total_characters": sum(len(chunk) for chunk in chunks),
                    "total_words": sum(len(chunk.split()) for chunk in chunks),
                    "avg_chunk_length": round(sum(len(chunk) for chunk in chunks) / len(chunks), 1) if chunks else 0,
                    "min_chunk_length": min(len(chunk) for chunk in chunks) if chunks else 0,
                    "max_chunk_length": max(len(chunk) for chunk in chunks) if chunks else 0
                }
            }
            
            with open(chunks_path, 'w', encoding='utf-8') as f:
                json.dump(chunks_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📄 Final chunks saved: {chunks_path}")
            return chunks_path
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save chunks: {e}")
            return chunks_path
    
    # HELPER FUNCTIONS
    def get_chunks_directory(self) -> str:
        """Get the chunks output directory path."""
        return str(self.chunks_directory)
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration settings."""
        return {
            "chunk_size": self.chunk_size,
            "semantic_threshold": self.semantic_threshold,
            "boundary_context": self.boundary_context,
            "concurrent_agents": self.concurrent_agents,
            "model_name": self.model_name,
            "chunks_directory": str(self.chunks_directory)
        }