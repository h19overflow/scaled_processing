# Pipelines package - Prefect-based processing pipelines

# Phase 1 Chonkie Migration - Unified pipeline architecture
from .document_processing import ChonkieProcessor, DoclingProcessor
from .rag_processing.flows import chonkie_rag_processing_flow, rag_processing_flow

__all__ = [
    'ChonkieProcessor',
    'DoclingProcessor',  # Backward compatibility alias
    'chonkie_rag_processing_flow', 
    'rag_processing_flow'  # Backward compatibility alias
]
