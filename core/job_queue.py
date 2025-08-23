"""
Job queue management for training runs.

Handles asynchronous job processing, queue management,
and background worker coordination.
"""

import asyncio
import logging
import time
import tempfile
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

from .run_store import get_run_store, RunStatus, TrainingRun
from .config import get_config


logger = logging.getLogger(__name__)


@dataclass 
class JobRequest:
    """A job request for the queue."""
    run_id: str
    kb_id: str
    base_model: str
    algo: str
    exp_name: str
    dataset_inline: Optional[List[Dict[str, str]]] = None
    dataset_url: Optional[str] = None
    idempotency_key: Optional[str] = None


class JobQueue:
    """Manages the training job queue and worker processes."""
    
    def __init__(self):
        self.config = get_config()
        self.run_store = get_run_store()
        
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: List[asyncio.Task] = []
        self._active_jobs: Dict[str, asyncio.Task] = {}
        self._idempotency_cache: Dict[str, str] = {}  # key -> run_id
        self._shutdown_event = asyncio.Event()
        self._running = False
    
    async def start(self) -> None:
        """Start the job queue and worker processes."""
        if self._running:
            return
            
        logger.info(f"Starting job queue with {self.config.max_concurrent_jobs} workers")
        
        self._running = True
        self._shutdown_event.clear()
        
        # Start worker tasks
        for i in range(self.config.max_concurrent_jobs):
            worker_task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._workers.append(worker_task)
    
    async def stop(self) -> None:
        """Stop the job queue and wait for workers to finish."""
        if not self._running:
            return
            
        logger.info("Stopping job queue")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel active jobs
        for job_task in self._active_jobs.values():
            job_task.cancel()
        
        # Wait for active jobs to finish/cancel
        if self._active_jobs:
            await asyncio.gather(*self._active_jobs.values(), return_exceptions=True)
        
        # Cancel and wait for workers
        for worker in self._workers:
            worker.cancel()
            
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        
        self._workers.clear()
        self._active_jobs.clear()
        self._running = False
        
        logger.info("Job queue stopped")
    
    async def submit_job(self, job: JobRequest) -> str:
        """
        Submit a job to the queue.
        
        Returns the run_id, handling idempotency if key is provided.
        """
        # Handle idempotency
        if job.idempotency_key:
            if job.idempotency_key in self._idempotency_cache:
                existing_run_id = self._idempotency_cache[job.idempotency_key]
                logger.info(f"Returning existing run {existing_run_id} for idempotency key {job.idempotency_key}")
                return existing_run_id
            
            # Cache the mapping
            self._idempotency_cache[job.idempotency_key] = job.run_id
            
            # Clean up old idempotency entries (keep for 10 minutes)
            asyncio.create_task(self._cleanup_idempotency_key(job.idempotency_key, 600))
        
        # Add to queue
        await self._queue.put(job)
        
        logger.info(f"Submitted job {job.run_id} to queue (queue size: {self._queue.qsize()})")
        return job.run_id
    
    async def get_queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
    async def get_active_job_count(self) -> int:
        """Get number of currently running jobs."""
        return len(self._active_jobs)
    
    async def cancel_job(self, run_id: str) -> bool:
        """Cancel a job if it's queued or running."""
        # Check if job is currently running
        if run_id in self._active_jobs:
            job_task = self._active_jobs[run_id]
            job_task.cancel()
            
            # Update run status
            await self.run_store.update_run_status(run_id, RunStatus.CANCELLED)
            
            logger.info(f"Cancelled running job {run_id}")
            return True
        
        # For queued jobs, we'd need to search the queue
        # This is complex with asyncio.Queue, so we'll update the run status
        # and let the worker handle it when it picks up the job
        run = await self.run_store.get_run(run_id)
        if run and run.status == RunStatus.QUEUED:
            await self.run_store.update_run_status(run_id, RunStatus.CANCELLED)
            logger.info(f"Marked queued job {run_id} as cancelled")
            return True
        
        return False
    
    async def _worker_loop(self, worker_name: str) -> None:
        """Main worker loop for processing jobs."""
        logger.info(f"Starting worker {worker_name}")
        
        while not self._shutdown_event.is_set():
            try:
                # Get next job with timeout
                try:
                    job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue  # Check shutdown event
                
                # Check if job was cancelled while queued
                run = await self.run_store.get_run(job.run_id)
                if not run or run.status == RunStatus.CANCELLED:
                    logger.info(f"Skipping cancelled job {job.run_id}")
                    continue
                
                # Process the job
                logger.info(f"Worker {worker_name} processing job {job.run_id}")
                
                # Create and track job task
                job_task = asyncio.create_task(self._process_job(job))
                self._active_jobs[job.run_id] = job_task
                
                try:
                    await job_task
                except asyncio.CancelledError:
                    logger.info(f"Job {job.run_id} was cancelled")
                except Exception as e:
                    logger.error(f"Job {job.run_id} failed with error: {e}")
                finally:
                    # Clean up
                    self._active_jobs.pop(job.run_id, None)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(1)  # Brief pause before retry
        
        logger.info(f"Worker {worker_name} stopped")
    
    async def _process_job(self, job: JobRequest) -> None:
        """Process a single training job."""
        run_id = job.run_id
        
        try:
            # Update status to running
            await self.run_store.update_run_status(run_id, RunStatus.RUNNING)
            
            # Prepare dataset
            dataset_path = await self._prepare_dataset(job)
            
            try:
                # Import training module
                from training import run_training
                
                # Run training
                result = run_training(
                    model_name=job.base_model,
                    datasets=["novalto"],  # Always use novalto for microservice
                    loss_config={"name": job.algo, "beta": 0.1},
                    exp_name=job.exp_name,
                    debug=False  # Disable wandb in production
                )
                
                # Update run with results
                await self.run_store.update_run_artifacts(
                    run_id,
                    checkpoint_url=result["artifact_path"],
                    logs_url=result["logs_path"]
                )
                
                # Mark as completed
                await self.run_store.update_run_status(run_id, RunStatus.COMPLETED)
                
                logger.info(f"Job {run_id} completed successfully")
                
            finally:
                # Clean up dataset file
                if os.path.exists(dataset_path):
                    os.remove(dataset_path)
                    
        except asyncio.CancelledError:
            # Job was cancelled
            await self.run_store.update_run_status(run_id, RunStatus.CANCELLED)
            raise
        except Exception as e:
            # Job failed
            error_msg = str(e)
            await self.run_store.update_run_status(run_id, RunStatus.FAILED, error_msg)
            logger.error(f"Job {run_id} failed: {error_msg}")
    
    async def _prepare_dataset(self, job: JobRequest) -> str:
        """Prepare dataset file for training."""
        # Create data directory
        data_dir = os.path.join(self.config.working_directory, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        # Use standard dataset.json name for novalto handler compatibility
        dataset_path = os.path.join(data_dir, "dataset.json")
        
        if job.dataset_inline:
            # Use inline dataset
            import json
            with open(dataset_path, "w") as f:
                json.dump(job.dataset_inline, f)
                
        elif job.dataset_url:
            # Fetch dataset from URL
            await self._fetch_dataset_from_url(job.dataset_url, dataset_path)
            
        else:
            raise ValueError("No dataset provided (neither inline nor URL)")
        
        return dataset_path
    
    async def _fetch_dataset_from_url(self, url: str, output_path: str) -> None:
        """Fetch dataset from URL and save to file."""
        import httpx
        import json
        import gzip
        
        # Validate URL scheme
        if not url.startswith(("https://", "http://")):
            raise ValueError("Dataset URL must use HTTPS or HTTP")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Check content size
            content_length = response.headers.get("content-length")
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > self.config.max_dataset_size_mb:
                    raise ValueError(f"Dataset too large: {size_mb:.1f}MB > {self.config.max_dataset_size_mb}MB")
            
            # Handle different content types
            content_type = response.headers.get("content-type", "")
            content = response.content
            
            if "gzip" in content_type or url.endswith(".gz"):
                # Decompress gzipped content
                content = gzip.decompress(content)
            
            # Parse and validate JSON
            if url.endswith(".jsonl") or url.endswith(".jsonl.gz"):
                # JSONL format - convert to list
                lines = content.decode('utf-8').strip().split('\n')
                data = [json.loads(line) for line in lines if line.strip()]
            else:
                # Regular JSON
                data = json.loads(content.decode('utf-8'))
            
            # Save to file
            with open(output_path, "w") as f:
                json.dump(data, f)
    
    async def _cleanup_idempotency_key(self, key: str, delay_seconds: int) -> None:
        """Remove idempotency key after delay."""
        await asyncio.sleep(delay_seconds)
        self._idempotency_cache.pop(key, None)


# Global job queue instance
_job_queue: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    """Get the global job queue instance."""
    global _job_queue
    if _job_queue is None:
        _job_queue = JobQueue()
    return _job_queue