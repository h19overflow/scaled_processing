"""
Database table setup script for the document processing system.
Creates all necessary PostgreSQL tables using SQLAlchemy models.
"""

import logging
import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.backend.doc_processing_system.core_deps.database.connection_manager import ConnectionManager
from src.backend.doc_processing_system.core_deps.database.models import Base


def setup_logging():
    """Setup logging for the table setup process."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def wait_for_database(connection_manager: ConnectionManager, max_retries: int = 30) -> bool:
    """Wait for database to be ready with retries."""
    logger = logging.getLogger(__name__)
    
    for attempt in range(max_retries):
        try:
            if connection_manager.health_check():
                logger.info("Database connection successful")
                return True
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}")
        
        if attempt < max_retries - 1:
            time.sleep(2)
    
    logger.error("Failed to connect to database after all retries")
    return False


def create_tables(connection_manager: ConnectionManager) -> bool:
    """Create all database tables."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Creating database tables...")
        connection_manager.create_tables()
        
        # Verify tables were created
        table_info = connection_manager.get_table_info()
        if table_info:
            logger.info(f"Successfully created {len(table_info)} tables:")
            for table_name, columns in table_info.items():
                logger.info(f"  - {table_name} ({len(columns)} columns)")
        else:
            logger.warning("No table information returned after creation")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False


def main():
    """Main function to setup database tables."""
    logger = setup_logging()
    logger.info("Starting database table setup...")
    
    try:
        # Initialize connection manager
        connection_manager = ConnectionManager()
        
        # Wait for database to be ready
        if not wait_for_database(connection_manager):
            logger.error("Database is not accessible. Exiting.")
            sys.exit(1)
        
        # Create tables
        if create_tables(connection_manager):
            logger.info("Database table setup completed successfully")
            sys.exit(0)
        else:
            logger.error("Database table setup failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Unexpected error during table setup: {e}")
        sys.exit(1)
    
    finally:
        try:
            connection_manager.close_connections()
        except:
            pass


if __name__ == "__main__":
    main()