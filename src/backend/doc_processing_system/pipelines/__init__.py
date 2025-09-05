# Pipelines package - Prefect-based processing pipelines

# Phase 1 Chonkie Migration - Unified pipeline architecture
try:
    from .document_processing.utils import DoclingProcessor
except ImportError:
    DoclingProcessor = None

__all__ = [
]

# Add DoclingProcessor to exports if available
if DoclingProcessor:
    __all__.append('DoclingProcessor')
