"""
In-memory run store for tracking training jobs.

Provides CRUD operations for training runs with status tracking,
metrics storage, and artifact URLs.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List, Any
from enum import Enum


logger = logging.getLogger(__name__)


class RunStatus(str, Enum):
    """
    Canonical status values for training runs.
    
    These are the only allowed status values - API responses will only
    emit these exact strings. Note: "succeeded" is NOT used, only "completed".
    """
    QUEUED = "queued"        # Job is queued for processing
    RUNNING = "running"      # Job is currently being processed
    COMPLETED = "completed"  # Job finished successfully (NOT "succeeded")
    FAILED = "failed"        # Job failed with an error
    CANCELLED = "cancelled"  # Job was cancelled by user or system


@dataclass
class TrainingRun:
    """A training run record."""
    run_id: str
    uid: str  # User ID from gateway claims
    kb_id: str  # Knowledge base ID
    exp_name: str
    base_model: str
    algo: str
    status: RunStatus
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    error_message: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    checkpoint_url: Optional[str] = None
    report_url: Optional[str] = None
    logs_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert run to dictionary for API responses."""
        data = asdict(self)
        # Convert float timestamps to integers for JSON
        for field in ['created_at', 'started_at', 'finished_at']:
            if data[field] is not None:
                data[field] = int(data[field])
        return data


class RunStore:
    """In-memory store for training runs."""
    
    def __init__(self):
        self._runs: Dict[str, TrainingRun] = {}
        self._lock = asyncio.Lock()
    
    async def create_run(
        self,
        uid: str,
        kb_id: str, 
        exp_name: str,
        base_model: str,
        algo: str
    ) -> TrainingRun:
        """Create a new training run."""
        run_id = str(uuid.uuid4())
        
        run = TrainingRun(
            run_id=run_id,
            uid=uid,
            kb_id=kb_id,
            exp_name=exp_name,
            base_model=base_model,
            algo=algo,
            status=RunStatus.QUEUED,
            created_at=time.time()
        )
        
        async with self._lock:
            self._runs[run_id] = run
            
        logger.info(f"Created run {run_id} for user {uid}, kb_id {kb_id}")
        return run
    
    async def get_run(self, run_id: str) -> Optional[TrainingRun]:
        """Get a run by ID."""
        async with self._lock:
            return self._runs.get(run_id)
    
    async def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """Update run status."""
        async with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return False
                
            old_status = run.status
            run.status = status
            run.error_message = error_message
            
            # Update timestamps based on status changes
            current_time = time.time()
            if status == RunStatus.RUNNING and old_status == RunStatus.QUEUED:
                run.started_at = current_time
            elif status in [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED]:
                if run.finished_at is None:
                    run.finished_at = current_time
            
            logger.info(f"Run {run_id} status changed: {old_status} -> {status}")
            return True
    
    async def update_run_artifacts(
        self,
        run_id: str,
        checkpoint_url: Optional[str] = None,
        report_url: Optional[str] = None, 
        logs_url: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update run artifacts and metrics."""
        async with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return False
                
            if checkpoint_url:
                run.checkpoint_url = checkpoint_url
            if report_url:
                run.report_url = report_url  
            if logs_url:
                run.logs_url = logs_url
            if metrics:
                run.metrics = metrics
                
            logger.info(f"Updated artifacts for run {run_id}")
            return True
    
    async def list_runs_for_user(self, uid: str, limit: int = 100) -> List[TrainingRun]:
        """List runs for a specific user."""
        async with self._lock:
            user_runs = [
                run for run in self._runs.values() 
                if run.uid == uid
            ]
            # Sort by creation time, newest first
            user_runs.sort(key=lambda r: r.created_at, reverse=True)
            return user_runs[:limit]
    
    async def count_active_runs_for_kb(self, uid: str, kb_id: str) -> int:
        """Count active (queued/running) runs for a kb_id."""
        async with self._lock:
            count = 0
            for run in self._runs.values():
                if (run.uid == uid and 
                    run.kb_id == kb_id and 
                    run.status in [RunStatus.QUEUED, RunStatus.RUNNING]):
                    count += 1
            return count
    
    async def get_queue_stats(self) -> Dict[str, int]:
        """Get statistics about the job queue."""
        async with self._lock:
            stats = {
                "total_runs": len(self._runs),
                "queued": 0,
                "running": 0, 
                "completed": 0,
                "failed": 0,
                "cancelled": 0
            }
            
            for run in self._runs.values():
                stats[run.status] += 1
                
            return stats
    
    async def cleanup_old_runs(self, max_age_seconds: int = 86400) -> int:
        """Remove runs older than max_age_seconds. Returns number removed."""
        cutoff_time = time.time() - max_age_seconds
        removed_count = 0
        
        async with self._lock:
            runs_to_remove = []
            for run_id, run in self._runs.items():
                # Only remove completed/failed/cancelled runs
                if (run.status in [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED] and
                    run.created_at < cutoff_time):
                    runs_to_remove.append(run_id)
            
            for run_id in runs_to_remove:
                del self._runs[run_id]
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old runs")
            
        return removed_count


# Global run store instance
_run_store: Optional[RunStore] = None


def get_run_store() -> RunStore:
    """Get the global run store instance."""
    global _run_store
    if _run_store is None:
        _run_store = RunStore()
    return _run_store