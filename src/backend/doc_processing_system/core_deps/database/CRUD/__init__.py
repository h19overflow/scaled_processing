"""
CRUD operations package.
Provides modular CRUD operations for all database entities.
"""

from .base_repository import BaseRepository
from .document_crud import DocumentCRUD

__all__ = [
    'BaseRepository',
    'DocumentCRUD',
]
