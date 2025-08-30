"""
Database components using SQLAlchemy for PostgreSQL connection and data access.
Contains connection manager, models, repository patterns, and modular CRUD operations.
"""

from .connection_manager import ConnectionManager
from .models import (
    DocumentModel,
    ChunkModel, 
    ExtractionResultModel,
    QueryLogModel,
    QueryResultModel,
    Base
)

from .CRUD import (
    BaseRepository,
    DocumentCRUD,
    ChunkCRUD,
    ExtractionCRUD,
    QueryCRUD
)

__all__ = [
    # Connection and Models
    "ConnectionManager",
    "DocumentModel",
    "ChunkModel",
    "ExtractionResultModel", 
    "QueryLogModel",
    "QueryResultModel",
    "Base",
    
    # CRUD Operations
    "BaseRepository",
    "DocumentCRUD",
    "ChunkCRUD",
    "ExtractionCRUD",
    "QueryCRUD"
]
