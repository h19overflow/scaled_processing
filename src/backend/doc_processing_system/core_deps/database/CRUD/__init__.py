"""
CRUD operations package.
Provides modular CRUD operations for all database entities.
"""

from .base_repository import BaseRepository
from .document_crud import DocumentCRUD
from .extraction_crud import ExtractionCRUD

__all__ = [
    'BaseRepository',
    'DocumentCRUD',
    'ExtractionCRUD',
]
