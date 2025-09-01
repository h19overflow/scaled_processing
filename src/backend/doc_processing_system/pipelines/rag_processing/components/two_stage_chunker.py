"""
Two-Stage Chunker - Complete 2-stage chunking orchestrator

Combines semantic chunking with agentic boundary refinement for optimal chunk boundaries.
Orchestrates the entire 2-stage process and provides comprehensive reporting.

Stage 1: Semantic chunking for initial context-aware splits
Stage 2: Agentic boundary review with merge/keep decisions

Dependencies: All component modules (semantic_chunker, boundary_agent)
Integration: Main interface for RAG pipeline chunking
"""

import json
import logging
import asyncio
import time
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
                 model_name: str = "gemini-2.0-flash",
                 output_directory: str = None):
        """Initialize the 2-stage chunker.
        
        Args:
            chunk_size: Target chunk size for semantic chunking
            semantic_threshold: Similarity threshold for semantic splits
            boundary_context: Context window for boundary analysis
            concurrent_agents: Number of concurrent boundary review agents
            model_name: LLM model for boundary decisions
            output_directory: Directory to save processing reports
        """
        self.chunk_size = chunk_size
        self.semantic_threshold = semantic_threshold
        self.boundary_context = boundary_context
        self.concurrent_agents = concurrent_agents
        self.model_name = model_name
        
        # Set output directory
        if output_directory:
            self.output_directory = Path(output_directory)
        else:
            self.output_directory = Path("src/backend/doc_processing_system/pipelines/rag_processing")
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
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
    
    async def process_document(self, text: str, document_id: str) -> Dict[str, Any]:
        """Process document through complete 2-stage chunking pipeline.
        
        Args:
            text: Document text content
            document_id: Unique document identifier
            
        Returns:
            Dict containing final chunks and comprehensive processing report
        """
        start_time = time.time()
        self.logger.info(f"🔄 Starting 2-stage chunking for {document_id}")
        
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
        
        # Build comprehensive report
        report = self._build_processing_report(
            document_id, text, stage1_result, stage2_result, 
            initial_chunks, final_chunks, total_processing_time
        )
        
        # Save report to JSON file
        report_path = self._save_processing_report(report, document_id)
        
        # Save final chunks to separate file
        chunks_path = self._save_chunks(final_chunks, document_id)
        
        return {
            "final_chunks": final_chunks,
            "chunk_count": len(final_chunks),
            "processing_report": report,
            "report_saved_path": str(report_path),
            "chunks_saved_path": str(chunks_path),
            "total_processing_time": total_processing_time
        }
    
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
    
    def _build_processing_report(self, 
                               document_id: str, 
                               original_text: str,
                               stage1_result: Dict[str, Any],
                               stage2_result: Dict[str, Any],
                               initial_chunks: List[str],
                               final_chunks: List[str],
                               total_time: float) -> Dict[str, Any]:
        """Build comprehensive processing report.
        
        Args:
            document_id: Document identifier
            original_text: Original document text
            stage1_result: Results from semantic chunking
            stage2_result: Results from boundary review
            initial_chunks: Chunks after stage 1
            final_chunks: Final chunks after stage 2
            total_time: Total processing time
            
        Returns:
            Comprehensive processing report
        """
        # Calculate final chunk statistics
        final_lengths = [len(chunk) for chunk in final_chunks]
        
        return {
            "document_info": {
                "document_id": document_id,
                "original_length": len(original_text),
                "processing_timestamp": datetime.now().isoformat()
            },
            "configuration": {
                "chunk_size": self.chunk_size,
                "semantic_threshold": self.semantic_threshold,
                "boundary_context": self.boundary_context,
                "concurrent_agents": self.concurrent_agents,
                "model_name": self.model_name
            },
            "stage1_semantic_chunking": {
                **stage1_result,
                "initial_chunks": initial_chunks  # Include initial chunks in report
            },
            "stage2_boundary_review": stage2_result,
            "final_results": {
                "initial_chunk_count": len(initial_chunks),
                "final_chunk_count": len(final_chunks),
                "chunks_merged": len(initial_chunks) - len(final_chunks),
                "merge_rate": round((len(initial_chunks) - len(final_chunks)) / len(initial_chunks) * 100, 1) if initial_chunks else 0,
                "final_chunk_statistics": {
                    "min_length": min(final_lengths) if final_lengths else 0,
                    "max_length": max(final_lengths) if final_lengths else 0,
                    "avg_length": round(sum(final_lengths) / len(final_lengths), 1) if final_lengths else 0,
                    "total_chars": sum(final_lengths)
                }
            },
            "performance_metrics": {
                "total_processing_time_seconds": round(total_time, 3),
                "stage1_time_seconds": stage1_result.get("processing_time_seconds", 0),
                "stage2_time_seconds": stage2_result.get("processing_time_seconds", 0),
                "chars_per_second": round(len(original_text) / total_time, 1) if total_time > 0 else 0
            },
            "quality_metrics": {
                "avg_boundary_confidence": stage2_result.get("avg_confidence", 0.0),
                "boundary_error_rate": round(stage2_result.get("error_decisions", 0) / max(stage2_result.get("total_boundaries", 1), 1) * 100, 1)
            }
        }
    
    def _save_processing_report(self, report: Dict[str, Any], document_id: str) -> Path:
        """Save processing report to JSON file.
        
        Args:
            report: Processing report dictionary
            document_id: Document identifier
            
        Returns:
            Path to saved report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chunking_report_{document_id}_{timestamp}.json"
        report_path = self.output_directory / filename
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📊 Processing report saved: {report_path}")
            return report_path
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save processing report: {e}")
            return report_path
    
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
        chunks_path = self.output_directory / filename
        
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
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration settings."""
        return {
            "chunk_size": self.chunk_size,
            "semantic_threshold": self.semantic_threshold,
            "boundary_context": self.boundary_context,
            "concurrent_agents": self.concurrent_agents,
            "model_name": self.model_name,
            "output_directory": str(self.output_directory)
        }
    
    def estimate_processing_time(self, text_length: int) -> float:
        """Estimate processing time based on text length.
        
        Args:
            text_length: Length of text in characters
            
        Returns:
            Estimated processing time in seconds
        """
        # Rough estimates based on typical performance
        # Stage 1: ~10k chars/second, Stage 2: ~5k chars/second  
        stage1_time = text_length / 10000
        stage2_time = text_length / 5000
        return stage1_time + stage2_time