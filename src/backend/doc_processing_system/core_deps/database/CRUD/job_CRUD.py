from src.backend.doc_processing_system.core_deps.database.CRUD.base_repository import BaseRepository
from src.backend.doc_processing_system.core_deps.database.models import JobModel,JobStatus
from datetime import datetime
from typing import Optional
from src.backend.doc_processing_system.core_deps.database.connection_manager import ConnectionManager
class JobCRUD(BaseRepository):
    """CRUD operations for job entities."""
    
    def __init__(self, connection_manager: ConnectionManager):
        super().__init__(connection_manager)

    def create_job(self, job: JobModel) -> str:
        """Create a new job."""
        with self.connection_manager.get_session() as session:
            session.add(job)
            session.commit()
            return job.job_id
    def get_job(self, job_id: str) -> JobModel:
        """Get a job by id."""
        with self.connection_manager.get_session() as session:
            job = session.query(JobModel).filter(JobModel.job_id == job_id).first()
            if job:
                return job
            else:
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
  