# add a docstring to the module and arrange the imports in a neat way
"""
Job CRUD operations.
Handles all database operations related to jobs.
"""

from src.backend.doc_processing_system.core_deps.database.CRUD.base_repository import BaseRepository
from src.backend.doc_processing_system.core_deps.database.models import JobModel,JobStatus
from src.backend.doc_processing_system.core_deps.database.connection_manager import ConnectionManager
from src.backend.doc_processing_system.messaging.message_schemas import create_message
from src.backend.doc_processing_system.messaging.producer import ProducerHandler
from typing import Optional
import os
from datetime import datetime
import uuid
from pathlib import Path

class JobCRUD(BaseRepository):
    """CRUD operations for job entities."""
    
    def __init__(self, connection_manager: ConnectionManager):
        super().__init__(connection_manager)
        self.producer = ProducerHandler("localhost:9092")
    def _generate_job_id(self) -> str:
        """Generate a new job ID."""
        return str(uuid.uuid4())
    
   
    def create_job(self, document_name: str, file_path: str) -> str:
        """Create a new job."""
        with self.connection_manager.get_session() as session:
            job_id = self._generate_job_id()
            session.add(JobModel(
                job_id=job_id,
                document_name=document_name,
                file_path=file_path
            ))
            session.commit()
            file_path_obj = Path(file_path)
            file_stat = os.stat(file_path)
        metadata = {
            "file_path": str(file_path_obj.absolute()),
            "file_name": document_name,
            "file_size": file_stat.st_size,
            "file_extension": file_path_obj.suffix.lower(),
            "created_time": file_stat.st_ctime,
            "job_id": job_id  # Include job_id for tracking
        }

        # Create standardized message
        message = create_message("file_detected", metadata, "api_upload")

        # Publish to Kafka (key is job_id for better tracking)
        success = self.producer.produce_message(
            topic="file_detected",
            key=job_id,
            value=message
        )
        
        return job_id, success
        
        
        
    def get_job(self, job_id: str) -> Optional[JobModel]:
        """
        Get a job by id.

        Returns a detached JobModel with all attributes eagerly loaded,
        safe to use outside the session context.

        Args:
            job_id: Job identifier

        Returns:
            JobModel if found, None otherwise
        """
        with self.connection_manager.get_session() as session:
            job = session.query(JobModel).filter(JobModel.job_id == job_id).first()

            if job:
                self.logger.info(f"Job {job.to_dict()} found")
                return job.to_dict()
            

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

            with self.connection_manager.get_session() as session:
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
  