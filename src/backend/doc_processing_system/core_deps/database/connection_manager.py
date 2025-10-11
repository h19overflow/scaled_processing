"""
SQLAlchemy connection manager for the document processing system.
Handles database connections, session management, and database initialization.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from ...config.settings import get_settings
from .models import Base


class ConnectionManager:
    """SQLAlchemy connection manager with session management."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize connection manager with database URL."""
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        # Load database URL from settings if not provided
        if database_url is None:
            settings = get_settings()
            database_url = settings.POSTGRES_DSN
        
        self.database_url = database_url
        
        # Create engine with connection pooling
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False  # Set to True for SQL debugging
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        self.logger.info(f"Connection manager initialized with database: {self._mask_password(database_url)}")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def create_tables(self) -> None:
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            self.logger.info("Database tables created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_tables(self) -> None:
        """Drop all database tables."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            self.logger.info("Database tables dropped successfully")
        except Exception as e:
            self.logger.error(f"Failed to drop tables: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def get_table_info(self) -> dict:
        """Get information about existing tables."""
        try:
            with self.get_session() as session:
                result = session.execute(text("""
                    SELECT table_name, column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name, ordinal_position
                """))
                
                tables = {}
                for row in result:
                    table_name = row[0]
                    if table_name not in tables:
                        tables[table_name] = []
                    tables[table_name].append({
                        'column': row[1],
                        'type': row[2]
                    })
                
                return tables
                
        except Exception as e:
            self.logger.error(f"Failed to get table info: {e}")
            return {}
    
    def execute_raw_query(self, query: str, params: dict = None) -> list:
        """Execute raw SQL query and return results."""
        try:
            with self.get_session() as session:
                result = session.execute(text(query), params or {})
                if result.returns_rows:
                    return [dict(row._mapping) for row in result]
                return []
        except Exception as e:
            self.logger.error(f"Raw query execution failed: {e}")
            raise
    
    def close_connections(self) -> None:
        """Close all database connections."""
        try:
            self.engine.dispose()
            self.logger.info("Database connections closed")
        except Exception as e:
            self.logger.error(f"Error closing connections: {e}")

    # JOB MANAGEMENT METHODS
    def create_job(self, job_id: str, document_name: str, file_path: str) -> bool:
        """
        Create a new job record with QUEUED status.

        Args:
            job_id: Unique job identifier
            document_name: Name of the document being processed
            file_path: Path to the uploaded file

        Returns:
            True if job created successfully, False otherwise
        """
        try:
            from .models import JobModel, JobStatus

            with self.get_session() as session:
                job = JobModel(
                    job_id=job_id,
                    document_name=document_name,
                    file_path=file_path,
                    status=JobStatus.QUEUED
                )
                session.add(job)
                session.commit()
                self.logger.info(f"Created job {job_id} for document {document_name}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to create job {job_id}: {e}")
            return False

    def get_job(self, job_id: str):
        """
        Retrieve job by job_id.

        Args:
            job_id: Job identifier

        Returns:
            JobModel instance if found, None otherwise
        """
        try:
            from .models import JobModel

            with self.get_session() as session:
                job = session.query(JobModel).filter(JobModel.job_id == job_id).first()
                if job:
                    # Detach from session to avoid lazy loading issues
                    session.expunge(job)
                return job
        except Exception as e:
            self.logger.error(f"Failed to get job {job_id}: {e}")
            return None

    def update_job_status(self, job_id: str, status: str, error: Optional[str] = None, bill_data: Optional[dict] = None) -> bool:
        """
        Update job status and optionally set error or bill_data.

        Args:
            job_id: Job identifier
            status: New status value (QUEUED, PROCESSING, COMPLETED, FAILED)
            error: Error message if status is FAILED
            bill_data: Extracted bill data if status is COMPLETED

        Returns:
            True if update successful, False otherwise
        """
        try:
            from .models import JobModel, JobStatus
            from datetime import datetime

            with self.get_session() as session:
                job = session.query(JobModel).filter(JobModel.job_id == job_id).first()

                if not job:
                    self.logger.warning(f"Job {job_id} not found for status update")
                    return False

                # Update status
                job.status = JobStatus[status.upper()]

                # Update error if provided
                if error:
                    job.error = error

                # Update bill_data if provided
                if bill_data:
                    job.bill_data = bill_data

                # Set completed_at timestamp if job is completed or failed
                if status.upper() in ["COMPLETED", "FAILED"]:
                    job.completed_at = datetime.utcnow()

                session.commit()
                self.logger.info(f"Updated job {job_id} status to {status}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to update job {job_id}: {e}")
            return False
    
    # HELPER FUNCTIONS
    def _setup_logging(self) -> None:
        """Setup logging for the connection manager."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _mask_password(self, database_url: str) -> str:
        """Mask password in database URL for logging."""
        if '@' in database_url:
            # Format: postgresql://user:password@host:port/db
            protocol_user_pass, host_db = database_url.split('@', 1)
            if ':' in protocol_user_pass:
                protocol_user, _ = protocol_user_pass.rsplit(':', 1)
                return f"{protocol_user}:***@{host_db}"
        return database_url