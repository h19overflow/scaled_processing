"""
Database components using SQLAlchemy for PostgreSQL connection and data access.
Contains connection manager, models, repository patterns, and modular CRUD operations.
"""

from .connection_manager import ConnectionManager
from .models import (
    DocumentModel,
    ChunkModel,
    StructuredDocumentModel,
    QueryLogModel,
    QueryResultModel,
    BillModel,
    BillStatus,
    Base
)

from .CRUD import (
    BaseRepository,
    DocumentCRUD,
    ExtractionCRUD,
)

__all__ = [
    # Connection and Models
    "ConnectionManager",
    "DocumentModel",
    "StructuredDocumentModel",
    "QueryLogModel",
    "QueryResultModel",
    "Base",
    
    # CRUD Operations
    "BaseRepository",
    "DocumentCRUD",
    "ExtractionCRUD",
]
