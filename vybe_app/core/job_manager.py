import queue
import threading
import time
import asyncio
import gc
import psutil
import os
from typing import Any, Callable, Dict, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import uuid

from ..logger import log_info, log_warning, log_error


class JobPriority(Enum):
    """Job priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class JobStatus(Enum):
    """Job status states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Job data structure"""
    id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: JobPriority
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None  # seconds


class PriorityJobQueue:
    """Priority-based job queue"""
    
    def __init__(self):
        self.queues = {
            JobPriority.CRITICAL: queue.Queue(),
            JobPriority.HIGH: queue.Queue(),
            JobPriority.NORMAL: queue.Queue(),
            JobPriority.LOW: queue.Queue()
        }
        self.lock = threading.Lock()
    
    def put(self, job: Job):
        """Add job to appropriate priority queue"""
        self.queues[job.priority].put(job)
    
    def get(self, timeout: Optional[int] = None) -> Optional[Job]:
        """Get next job from highest priority non-empty queue"""
        if timeout is None:
            # Non-blocking mode
            for priority in [JobPriority.CRITICAL, JobPriority.HIGH, JobPriority.NORMAL, JobPriority.LOW]:
                try:
                    return self.queues[priority].get_nowait()
                except queue.Empty:
                    continue
            return None
        else:
            # Blocking mode with timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                for priority in [JobPriority.CRITICAL, JobPriority.HIGH, JobPriority.NORMAL, JobPriority.LOW]:
                    try:
                        return self.queues[priority].get_nowait()
                    except queue.Empty:
                        continue
                # Use short wait instead of sleep to prevent busy waiting
                time.sleep(0.01)  # Reduced delay to improve responsiveness
            return None
    
    def empty(self) -> bool:
        """Check if all queues are empty"""
        return all(q.empty() for q in self.queues.values())


class JobManager:
    """
    Advanced thread-safe background job queue manager with priority support,
    scheduling, and async processing capabilities.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Ensure only one instance of JobManager exists (singleton pattern)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(JobManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the job queue and worker threads."""
        if hasattr(self, '_initialized'):
            return
        
        self.job_queue = PriorityJobQueue()
        self.jobs: Dict[str, Job] = {}
        self.worker_threads = []
        self.max_workers = 4
        self._running = False
        self._initialized = True
        
        # Resource management
        self.cleanup_interval = 300  # 5 minutes
        self.job_retention_hours = 24  # Keep job results for 24 hours
        self.max_memory_usage = 0.8  # 80% memory threshold
        self.cleanup_thread = None
        self.last_cleanup = datetime.now()
        
        # Job statistics
        self.stats = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'pending_jobs': 0,
            'cleaned_jobs': 0,
            'memory_usage_mb': 0
        }
    
    def start(self, worker_count: Optional[int] = None):
        """Start worker threads to process jobs from the queue."""
        if worker_count:
            self.max_workers = worker_count
        
        if not self._running:
            self._running = True
            
            # Start worker threads
            for i in range(self.max_workers):
                worker = threading.Thread(target=self._job_runner, daemon=True, name=f"JobWorker-{i}")
                worker.start()
                self.worker_threads.append(worker)
            
            # Start cleanup thread
            self.cleanup_thread = threading.Thread(target=self._cleanup_runner, daemon=True, name="JobCleanup")
            self.cleanup_thread.start()
            
            log_info(f"Job manager started with {self.max_workers} workers and cleanup monitoring")
    
    def stop(self):
        """Gracefully shut down all worker threads."""
        if self._running:
            self._running = False
            
            # Signal cleanup thread to stop
            if hasattr(self, "_stop_cleanup_event"):
                self._stop_cleanup_event.set()
            
            # Wait for all workers to finish
            for worker in self.worker_threads:
                if worker.is_alive():
                    worker.join(timeout=5)
            
            # Wait for cleanup thread to finish
            if self.cleanup_thread and self.cleanup_thread.is_alive():
                self.cleanup_thread.join(timeout=5)
            
            self.worker_threads.clear()
            self.cleanup_thread = None
            
            # Final cleanup
            self._perform_cleanup(force=True)
            log_info("Job manager stopped")
    
    def is_running(self) -> bool:
        """Return True if the job manager is active."""
        try:
            return bool(self._running and any(w.is_alive() for w in self.worker_threads))
        except Exception:
            return False
    
    def add_job(self, func: Callable, *args, priority: JobPriority = JobPriority.NORMAL, 
                timeout: Optional[int] = None, max_retries: int = 3, **kwargs) -> str:
        """
        Add a job to the queue for background execution.
        
        Args:
            func: The function to execute
            *args: Positional arguments for the function
            priority: Job priority level
            timeout: Job timeout in seconds
            max_retries: Maximum retry attempts
            **kwargs: Keyword arguments for the function
            
        Returns:
            Job ID for tracking
        """
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
            timeout=timeout,
            max_retries=max_retries
        )
        
        self.jobs[job_id] = job
        self.job_queue.put(job)
        self.stats['total_jobs'] += 1
        self.stats['pending_jobs'] += 1
        
        log_info(f"Added job {job_id} with priority {priority.name}")
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and details"""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        return {
            'id': job.id,
            'status': job.status.value,
            'priority': job.priority.name,
            'created_at': job.created_at.isoformat(),
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'result': job.result,
            'error': job.error,
            'retry_count': job.retry_count
        }
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        if job.status == JobStatus.PENDING:
            job.status = JobStatus.CANCELLED
            self.stats['pending_jobs'] -= 1
            log_info(f"Cancelled job {job_id}")
            return True
        
        return False
    
    def force_cleanup(self):
        """Manually trigger cleanup of old jobs and memory optimization"""
        self._perform_cleanup(force=True)
        log_info("Manual cleanup completed")
    
    def configure_cleanup(self, cleanup_interval: Optional[int] = None, 
                         job_retention_hours: Optional[int] = None,
                         max_memory_usage: Optional[float] = None):
        """Configure cleanup settings"""
        if cleanup_interval is not None:
            self.cleanup_interval = max(60, cleanup_interval)  # Minimum 1 minute
        if job_retention_hours is not None:
            self.job_retention_hours = max(1, job_retention_hours)  # Minimum 1 hour
        if max_memory_usage is not None:
            self.max_memory_usage = max(0.5, min(0.95, max_memory_usage))  # Between 50% and 95%
        
        log_info(f"Cleanup configured: interval={self.cleanup_interval}s, retention={self.job_retention_hours}h, memory_threshold={self.max_memory_usage*100:.1f}%")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get job manager statistics"""
        # Update memory usage
        self._update_memory_usage()
        
        return {
            'stats': self.stats.copy(),
            'active_workers': len([w for w in self.worker_threads if w.is_alive()]),
            'pending_jobs': self.stats['pending_jobs'],
            'total_jobs': len(self.jobs),
            'memory_usage_mb': self.stats['memory_usage_mb'],
            'last_cleanup': self.last_cleanup.isoformat(),
            'cleanup_interval_seconds': self.cleanup_interval,
            'job_retention_hours': self.job_retention_hours
        }
    
    def _cleanup_runner(self):
        """Cleanup thread function for periodic resource management"""
        # Use stop event for graceful shutdown
        self._stop_cleanup_event = getattr(self, "_stop_cleanup_event", threading.Event())
        
        while self._running and not self._stop_cleanup_event.is_set():
            try:
                # Wait for cleanup interval or stop signal
                self._stop_cleanup_event.wait(self.cleanup_interval)
                if self._running and not self._stop_cleanup_event.is_set():
                    self._perform_cleanup()
            except Exception as e:
                log_error(f"Cleanup runner error: {e}")
    
    def _perform_cleanup(self, force: bool = False):
        """Perform periodic cleanup of completed jobs and memory optimization"""
        try:
            current_time = datetime.now()
            
            # Check if cleanup is needed
            if not force and (current_time - self.last_cleanup).total_seconds() < self.cleanup_interval:
                return
            
            # Clean up old completed jobs
            jobs_to_remove = []
            cutoff_time = current_time - timedelta(hours=self.job_retention_hours)
            
            for job_id, job in self.jobs.items():
                if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED] and 
                    job.completed_at and job.completed_at < cutoff_time):
                    jobs_to_remove.append(job_id)
            
            # Remove old jobs
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
                self.stats['cleaned_jobs'] += 1
            
            # Memory optimization
            self._optimize_memory()
            
            # Update cleanup timestamp
            self.last_cleanup = current_time
            
            if jobs_to_remove:
                log_info(f"Cleaned up {len(jobs_to_remove)} old jobs, total jobs: {len(self.jobs)}")
                
        except Exception as e:
            log_error(f"Error during cleanup: {e}")
    
    def _optimize_memory(self):
        """Optimize memory usage through garbage collection and monitoring"""
        try:
            # Force garbage collection
            collected = gc.collect()
            
            # Update memory usage statistics
            self._update_memory_usage()
            
            # Check if memory usage is high
            if self.stats['memory_usage_mb'] > 0:
                process = psutil.Process(os.getpid())
                memory_percent = process.memory_percent()
                
                if memory_percent > (self.max_memory_usage * 100):
                    log_warning(f"High memory usage detected: {memory_percent:.1f}%")
                    
                    # Force more aggressive cleanup
                    gc.collect()
                    
                    # Clear job results for completed jobs older than 1 hour
                    current_time = datetime.now()
                    cutoff_time = current_time - timedelta(hours=1)
                    
                    for job in self.jobs.values():
                        if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED] and 
                            job.completed_at and job.completed_at < cutoff_time):
                            job.result = None  # Clear large result objects
            
            if collected > 0:
                log_info(f"Garbage collection freed {collected} objects")
                
        except Exception as e:
            log_error(f"Error during memory optimization: {e}")
    
    def _update_memory_usage(self):
        """Update memory usage statistics"""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            self.stats['memory_usage_mb'] = memory_info.rss / 1024 / 1024  # Convert to MB
        except Exception as e:
            log_error(f"Error updating memory usage: {e}")
    
    def _job_runner(self):
        """Worker thread function"""
        while self._running:
            try:
                job = self.job_queue.get(timeout=1)
                if job is None:
                    break
                
                self._execute_job(job)
                
            except queue.Empty:
                continue
            except Exception as e:
                log_error(f"Job runner error: {e}")
    
    def _execute_job(self, job: Job):
        """Execute a single job"""
        try:
            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            self.stats['pending_jobs'] -= 1
            
            log_info(f"Executing job {job.id}")
            
            # Execute with timeout if specified
            if job.timeout:
                import concurrent.futures
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(job.func, *job.args, **job.kwargs)
                    try:
                        result = future.result(timeout=job.timeout)
                    except concurrent.futures.TimeoutError:
                        future.cancel()
                        raise TimeoutError(f"Job {job.id} timed out after {job.timeout} seconds")
            else:
                result = job.func(*job.args, **job.kwargs)
            
            # Job completed successfully
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.result = result
            self.stats['completed_jobs'] += 1
            
            log_info(f"Job {job.id} completed successfully")
            
        except Exception as e:
            # Job failed
            job.error = str(e)
            job.retry_count += 1
            
            if job.retry_count <= job.max_retries:
                # Retry job
                job.status = JobStatus.PENDING
                self.stats['pending_jobs'] += 1
                self.job_queue.put(job)
                log_warning(f"Job {job.id} failed, retrying ({job.retry_count}/{job.max_retries}): {e}")
            else:
                # Job failed permanently
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now()
                self.stats['failed_jobs'] += 1
                log_error(f"Job {job.id} failed permanently after {job.max_retries} retries: {e}")
    
    def add_document_processing_job(self, content: str, filename: str, collection_name: str = "default"):
        """
        Add a document processing job for automatic RAG ingestion with LLM processing.
        
        Args:
            content: Document content to process
            filename: Name of the file
            collection_name: ChromaDB collection name
        """
        def process_document_task():
            try:
                # Import backend LLM controller here to avoid circular imports
                from .backend_llm_controller import BackendLLMController
                backend_llm = BackendLLMController()
                
                # Process with backend LLM for summary and tags
                from ..rag.text_processing import process_document_with_llm, ingest_file_content_to_rag
                llm_result = process_document_with_llm(content, filename, backend_llm)
                
                # Ingest into RAG with processed metadata
                success = ingest_file_content_to_rag(collection_name, filename, content)
                
                if success:
                    log_info(f"Successfully processed and ingested document: {filename}")
                    return {
                        'success': True,
                        'filename': filename,
                        'summary': llm_result['summary'][:100],
                        'tags': llm_result['tags']
                    }
                else:
                    log_error(f"Failed to ingest document: {filename}")
                    return {'success': False, 'filename': filename}
                    
            except Exception as e:
                log_error(f"Error processing document {filename}: {e}")
                return {'success': False, 'filename': filename, 'error': str(e)}
        
        return self.add_job(process_document_task, priority=JobPriority.NORMAL, timeout=300)


# Global singleton instance
job_manager = JobManager()
