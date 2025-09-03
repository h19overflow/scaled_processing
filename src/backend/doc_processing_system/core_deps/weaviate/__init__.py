"""
Weaviate integration components for the document processing system.
Drop-in replacement for ChromaDB components with identical interfaces.
"""

from .weaviate_manager import WeaviateManager
from .weaviate_ingestion_engine import WeaviateIngestionEngine

# Export for interface compatibility 
ChromaManager = WeaviateManager  # Alias for drop-in replacement
ChunkIngestionEngine = WeaviateIngestionEngine  # Alias for drop-in replacement

__all__ = [
    "WeaviateManager",
    "WeaviateIngestionEngine", 
    "ChromaManager",  # Drop-in replacement alias
    "ChunkIngestionEngine",  # Drop-in replacement alias
]