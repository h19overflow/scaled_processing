"""
CRUD operations package.
Provides modular CRUD operations for all database entities.
"""

from .base_repository import BaseRepository
from .document_crud import DocumentCRUD
from .chunk_crud import ChunkCRUD
from .extraction_crud import ExtractionCRUD
from .query_crud import QueryCRUD
from .temporal_crud import TemporalCRUD

__all__ = [
    'BaseRepository',
    'DocumentCRUD',
    'ChunkCRUD',
    'ExtractionCRUD',
    'QueryCRUD',
    'TemporalCRUD'
]
