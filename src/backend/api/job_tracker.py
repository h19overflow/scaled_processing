"""
In-memory job tracking for async document processing.

Tracks job status, metadata, and results during document processing lifecycle.
Thread-safe for concurrent access from multiple API workers.
"""

import threading
from typing import Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class JobInfo:
    """Job information container."""
    job_id: str
    status: str  # queued, processing, completed, failed
    document_name: str
    file_path: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    bill_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class JobTracker:
    """
    Thread-safe in-memory job tracker.

    Stores job metadata and status for async document processing.
    Uses threading.Lock for concurrent access protection.
    """

    def __init__(self):
        """Initialize job tracker with empty job storage."""
        self._jobs: Dict[str, JobInfo] = {}
        self._lock = threading.Lock()

    def create_job(self, job_id: str, document_name: str, file_path: str) -> JobInfo:
        """
        Create new job with queued status.

        Args:
            job_id: Unique job identifier
            document_name: Original filename
            file_path: Path to uploaded file

        Returns:
            Created JobInfo object
        """
        with self._lock:
            job = JobInfo(
                job_id=job_id,
                status="queued",
                document_name=document_name,
                file_path=file_path
            )
            self._jobs[job_id] = job
            return job

    def get_job(self, job_id: str) -> Optional[JobInfo]:
        """
        Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            JobInfo if found, None otherwise
        """
        with self._lock:
            return self._jobs.get(job_id)

    def update_status(self, job_id: str, status: str) -> None:
        """
        Update job status.

        Args:
            job_id: Job identifier
            status: New status (queued, processing, completed, failed)
        """
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].status = status
                if status in ("completed", "failed"):
                    self._jobs[job_id].completed_at = datetime.utcnow()

    def set_result(self, job_id: str, bill_data: Dict[str, Any]) -> None:
        """
        Set job result data.

        Args:
            job_id: Job identifier
            bill_data: Extracted bill data dictionary
        """
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].bill_data = bill_data
                self._jobs[job_id].status = "completed"
                self._jobs[job_id].completed_at = datetime.utcnow()

    def set_error(self, job_id: str, error: str) -> None:
        """
        Set job error.

        Args:
            job_id: Job identifier
            error: Error message
        """
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].error = error
                self._jobs[job_id].status = "failed"
                self._jobs[job_id].completed_at = datetime.utcnow()

    def cleanup_old_jobs(self, max_age_seconds: int = 3600) -> int:
        """
        Remove completed/failed jobs older than max_age_seconds.

        Args:
            max_age_seconds: Maximum age in seconds (default 1 hour)

        Returns:
            Number of jobs cleaned up
        """
        with self._lock:
            now = datetime.utcnow()
            jobs_to_remove = [
                job_id for job_id, job in self._jobs.items()
                if job.completed_at and (now - job.completed_at).total_seconds() > max_age_seconds
            ]
            for job_id in jobs_to_remove:
                del self._jobs[job_id]
            return len(jobs_to_remove)

    def get_all_jobs(self) -> Dict[str, JobInfo]:
        """
        Get all jobs (for debugging).

        Returns:
            Dictionary of all jobs
        """
        with self._lock:
            return self._jobs.copy()
