"""
Base repository with common functionality.
Provides shared methods and initialization for all CRUD repositories.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from ..connection_manager import ConnectionManager


class BaseRepository:
    """Base repository with common functionality."""
    
    def __init__(self, connection_manager: ConnectionManager):
        """Initialize repository with connection manager.
        
        Args:
            connection_manager: Database connection manager instance
        """
        self.connection_manager = connection_manager
        self.logger = logging.getLogger(__name__)
    
    def _convert_uuid_to_str(self, uuid_obj: UUID) -> str:
        """Convert UUID object to string.
        
        Args:
            uuid_obj: UUID object to convert
            
        Returns:
            str: String representation of UUID
        """
        return str(uuid_obj) if uuid_obj else None
    
    def _validate_uuid(self, uuid_str: str) -> UUID:
        """Validate and convert string to UUID.
        
        Args:
            uuid_str: String representation of UUID
            
        Returns:
            UUID: Validated UUID object
            
        Raises:
            ValueError: If UUID string is invalid
        """
        try:
            return UUID(uuid_str)
        except (ValueError, TypeError) as e:
            self.logger.error(f"Invalid UUID format: {uuid_str}")
            raise ValueError(f"Invalid UUID format: {uuid_str}") from e
    
    def _log_operation(self, operation: str, entity_id: str = None, details: str = None):
        """Log database operation.
        
        Args:
            operation: Description of the operation
            entity_id: ID of the entity being operated on
            details: Additional operation details
        """
        log_msg = f"{operation}"
        if entity_id:
            log_msg += f" - ID: {entity_id}"
        if details:
            log_msg += f" - {details}"
        
        self.logger.info(log_msg)
