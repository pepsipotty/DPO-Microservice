"""
Progress reporting for training jobs.

Provides real-time progress updates, ETA calculation, and phase tracking
during training execution.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any

from .run_store import get_run_store

logger = logging.getLogger(__name__)


class ProgressReporter:
    """Reports training progress and updates run status."""
    
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.run_store = get_run_store()
        self.start_time = time.time()
        self._last_update_time = time.time()
        
    async def update_phase(self, phase: str, message: str = ""):
        """Update the current training phase."""
        await self.run_store.update_run_progress(
            self.run_id,
            current_phase=phase,
            phase_message=message
        )
        logger.info(f"Run {self.run_id}: {phase} - {message}")
    
    async def update_progress(
        self,
        current_step: Optional[int] = None,
        total_steps: Optional[int] = None,
        current_epoch: Optional[int] = None,
        total_epochs: Optional[int] = None,
        metrics: Optional[Dict[str, float]] = None,
        message: str = ""
    ):
        """Update training progress with step/epoch information."""
        
        # Calculate progress percentage
        progress_percentage = self._calculate_progress(
            current_step, total_steps, current_epoch, total_epochs
        )
        
        # Calculate ETA
        eta_seconds = self._calculate_eta(progress_percentage)
        
        # Update run store
        await self.run_store.update_run_progress(
            self.run_id,
            current_step=current_step,
            total_steps=total_steps,
            current_epoch=current_epoch,
            total_epochs=total_epochs,
            progress_percentage=progress_percentage,
            eta_seconds=eta_seconds,
            last_metrics=metrics,
            phase_message=message
        )
        
        # Log progress (throttled to avoid spam)
        current_time = time.time()
        if current_time - self._last_update_time >= 10:  # Log every 10 seconds max
            logger.info(f"Run {self.run_id}: {progress_percentage:.1f}% - {message}")
            self._last_update_time = current_time
    
    async def set_total_steps(self, total_steps: int, total_epochs: int = 1):
        """Set the total number of steps and epochs for progress calculation."""
        await self.run_store.update_run_progress(
            self.run_id,
            total_steps=total_steps,
            total_epochs=total_epochs
        )
    
    async def update_metrics(self, metrics: Dict[str, float], message: str = ""):
        """Update current training metrics."""
        await self.run_store.update_run_progress(
            self.run_id,
            last_metrics=metrics,
            phase_message=message
        )
    
    def _calculate_progress(
        self,
        current_step: Optional[int],
        total_steps: Optional[int],
        current_epoch: Optional[int],
        total_epochs: Optional[int]
    ) -> float:
        """Calculate progress percentage based on steps and epochs."""
        if not total_steps or total_steps <= 0:
            return 0.0
            
        if not current_step:
            current_step = 0
            
        if total_epochs and total_epochs > 1:
            # Multi-epoch training: combine epoch and step progress
            if current_epoch is None:
                current_epoch = 1
            
            epoch_progress = (current_epoch - 1) / total_epochs
            step_progress = current_step / total_steps / total_epochs
            return (epoch_progress + step_progress) * 100
        else:
            # Single epoch: just step progress
            return (current_step / total_steps) * 100
    
    def _calculate_eta(self, progress_percentage: float) -> Optional[float]:
        """Calculate estimated time to completion."""
        if progress_percentage <= 0:
            return None
            
        elapsed = time.time() - self.start_time
        if elapsed < 30:  # Need at least 30 seconds of data for reliable ETA
            return None
            
        rate = progress_percentage / elapsed  # percentage per second
        if rate <= 0:
            return None
            
        remaining_progress = 100 - progress_percentage
        return remaining_progress / rate