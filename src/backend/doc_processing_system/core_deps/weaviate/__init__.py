"""
Weaviate integration components for the document processing system.
Drop-in replacement for ChromaDB components with identical interfaces.
"""

from .weaviate_manager import WeaviateManager

# Export for interface compatibility 
ChromaManager = WeaviateManager  # Alias for drop-in replacement

__all__ = [
    "WeaviateManager",
    "ChromaManager",  # Drop-in replacement alias
]