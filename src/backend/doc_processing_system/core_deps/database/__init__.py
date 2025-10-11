"""
Database components using SQLAlchemy for PostgreSQL connection and data access.
Contains connection manager, models, repository patterns, and modular CRUD operations.
"""

from .connection_manager import ConnectionManager
from .models import (
    DocumentModel,
    BillModel,
    BillStatus,
    Base
)

from .CRUD import (
    BaseRepository,
    DocumentCRUD,
)

__all__ = [
    # Connection and Models
    "ConnectionManager",
    "DocumentModel",
    "BillModel",
    "BillStatus",
    "Base",

    # CRUD Operations
    "BaseRepository",
    "DocumentCRUD",
]
