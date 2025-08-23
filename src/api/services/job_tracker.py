"""
Job tracking service untuk background processing
"""

import logging
import uuid
import asyncio
import threading
from typing import Dict, Optional, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class JobStatus(str, Enum):
    """Job status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobInfo:
    """Job information class"""
    
    def __init__(self, job_id: str, job_type: str, params: Dict[str, Any]):
        self.job_id = job_id
        self.job_type = job_type
        self.params = params
        self.status = JobStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.progress = 0  # 0-100
        self.message = ""
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.logs = []
        self.cancel_requested = False  # Flag untuk cancel request
        self.thread_ref: Optional[threading.Thread] = None  # Reference ke thread

    def update_progress(self, progress: int, message: str = ""):
        """Update job progress"""
        self.progress = max(0, min(100, progress))
        self.message = message
        self.logs.append({
            "timestamp": datetime.now(),
            "progress": self.progress,
            "message": message
        })
        logger.info(f"Job {self.job_id}: {self.progress}% - {message}")

    def start(self):
        """Mark job as started"""
        self.status = JobStatus.PROCESSING
        self.started_at = datetime.now()
        self.update_progress(0, "Job started")

    def complete(self, result: Dict[str, Any]):
        """Mark job as completed"""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result
        self.update_progress(100, "Job completed successfully")

    def fail(self, error: str):
        """Mark job as failed"""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.now()
        self.error = error
        self.message = f"Job failed: {error}"
        logger.error(f"Job {self.job_id} failed: {error}")
    
    def cancel(self):
        """Request job cancellation"""
        self.cancel_requested = True
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.now()
        self.message = "Job cancelled by user"
        logger.info(f"Job {self.job_id} cancellation requested")
    
    def is_cancelled(self) -> bool:
        """Check if job cancellation is requested"""
        return self.cancel_requested

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "params": {
                "form_url": self.params.get("form_url", ""),
                "filename": self.params.get("filename", ""),
                "rows_count": self.params.get("rows_count", 0),
                "headless": self.params.get("headless", True),
                "threads": self.params.get("threads", 1)
            }
        }

class JobTracker:
    """Job tracking service"""
    
    def __init__(self):
        self.jobs: Dict[str, JobInfo] = {}
        self._lock = threading.Lock()
    
    def create_job(self, job_type: str, params: Dict[str, Any]) -> str:
        """Create new job and return job ID"""
        job_id = str(uuid.uuid4())
        
        with self._lock:
            job_info = JobInfo(job_id, job_type, params)
            self.jobs[job_id] = job_info
            
        logger.info(f"Created job {job_id} - Type: {job_type}")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[JobInfo]:
        """Get job info by ID"""
        with self._lock:
            return self.jobs.get(job_id)
    
    def update_job_progress(self, job_id: str, progress: int, message: str = ""):
        """Update job progress"""
        with self._lock:
            job = self.jobs.get(job_id)
            if job:
                job.update_progress(progress, message)
    
    def start_job(self, job_id: str):
        """Mark job as started"""
        with self._lock:
            job = self.jobs.get(job_id)
            if job:
                job.start()
    
    def complete_job(self, job_id: str, result: Dict[str, Any]):
        """Mark job as completed"""
        with self._lock:
            job = self.jobs.get(job_id)
            if job:
                job.complete(result)
    
    def fail_job(self, job_id: str, error: str):
        """Mark job as failed"""
        with self._lock:
            job = self.jobs.get(job_id)
            if job:
                job.fail(error)
    
    def get_all_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Get all jobs"""
        with self._lock:
            return {job_id: job.to_dict() for job_id, job in self.jobs.items()}
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old completed jobs"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        with self._lock:
            jobs_to_remove = []
            for job_id, job in self.jobs.items():
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    if job.completed_at and job.completed_at.timestamp() < cutoff_time:
                        jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
                logger.info(f"Cleaned up old job: {job_id}")

# Global job tracker instance
job_tracker = JobTracker()