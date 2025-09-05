"""
RAG Processing Flows Package

Phase 1 Migration: Unified Chonkie-based RAG processing pipeline
Replaces 5-stage pipeline with single unified flow for 2-33x performance improvement

Main Flow:
- chonkie_rag_processing_flow: Unified pipeline with integrated chunking + embeddings + storage
"""

# Phase 1: Chonkie unified pipeline
from .chonkie_rag_flow import (
    chonkie_rag_processing_flow,
    process_document_via_rag_pipeline
)

# Backward compatibility aliases (redirects to Chonkie implementations)
rag_processing_flow = chonkie_rag_processing_flow

# Legacy task aliases (deprecated - all handled by unified Chonkie pipeline)
semantic_chunking_task = None  # Integrated into chonkie_rag_processing_flow
boundary_refinement_task = None  # Integrated into chonkie_rag_processing_flow
chunk_formatting_task = None  # Integrated into chonkie_rag_processing_flow
generate_embeddings_task = None  # Integrated into chonkie_rag_processing_flow
store_vectors_task = None  # Integrated into chonkie_rag_processing_flow

__all__ = [
    "chonkie_rag_processing_flow",
    "rag_processing_flow",  # Backward compatibility alias
    "process_document_via_rag_pipeline",
    # Legacy tasks (deprecated)
    "semantic_chunking_task",
    "boundary_refinement_task",
    "chunk_formatting_task", 
    "generate_embeddings_task",
    "store_vectors_task"
]