"""
Database components using SQLAlchemy for PostgreSQL connection and data access.
Contains connection manager, models, repository patterns, and modular CRUD operations.
"""

from .connection_manager import ConnectionManager
from .models import (
    DocumentModel,
    StructuredDocumentModel,
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
    "BillModel",
    "BillStatus",
    "Base",

    # CRUD Operations
    "BaseRepository",
    "DocumentCRUD",
    "ExtractionCRUD",
]
