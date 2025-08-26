"""
DPO Microservice - Ephemeral-Friendly Gateway Integration

FastAPI service that integrates with the stable gateway for DPO training.
Supports HMAC authentication, job queuing, and run management.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Union, Any

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn

from core.config import get_config
from core.auth import verify_request_auth, UserClaims, extract_user_claims
from core.registration import start_registration, stop_registration
from core.run_store import get_run_store, RunStatus
from core.job_queue import get_job_queue, JobRequest


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Request/Response Models
class DPORecord(BaseModel):
    """A single DPO training record in standard DPO format."""
    prompt: str = Field(..., min_length=1, description="The input prompt")
    responses: List[str] = Field(..., min_items=2, description="List of response options")
    pairs: List[List[int]] = Field(..., min_items=1, description="Preference pairs as [preferred_idx, rejected_idx]")
    sft_target: str = Field(..., min_length=1, description="The best response for SFT pre-training")


class TriggerFinetuneRequest(BaseModel):
    """Request model for trigger-finetune endpoint."""
    kb_id: str = Field(..., min_length=1, description="Knowledge base identifier")
    base_model: str = Field("zephyr", description="Base model to fine-tune")
    algo: str = Field("dpo", description="Training algorithm")
    exp_name: str = Field(..., min_length=1, description="Experiment name")
    
    # Dataset options - exactly one must be provided
    dataset_inline: Optional[List[DPORecord]] = Field(None, description="Inline dataset records")
    dataset_url: Optional[str] = Field(None, description="URL to fetch dataset from")
    
    @validator('dataset_url')
    def validate_dataset_url(cls, v):
        if v and not v.startswith(('https://', 'http://')):
            raise ValueError("Dataset URL must use HTTPS or HTTP")
        return v
    
    def __init__(self, **data):
        super().__init__(**data)
        # Ensure exactly one dataset option is provided
        has_inline = self.dataset_inline is not None
        has_url = self.dataset_url is not None
        
        if not has_inline and not has_url:
            raise ValueError("Must provide either dataset_inline or dataset_url")
        if has_inline and has_url:
            raise ValueError("Cannot provide both dataset_inline and dataset_url")


class TriggerFinetuneResponse(BaseModel):
    """Response model for trigger-finetune endpoint."""
    run_id: str
    status: str = "queued"


class RunStatusResponse(BaseModel):
    """
    Response model for run status.
    
    Status will be one of: "queued", "running", "completed", "failed", "cancelled"
    (never "succeeded" - only "completed" is used for successful runs)
    """
    run_id: str
    status: str  # One of the canonical RunStatus values
    metrics: Optional[Dict[str, Any]] = None
    started_at: Optional[int] = None  # Unix timestamp
    finished_at: Optional[int] = None  # Unix timestamp
    
    # Progress tracking fields
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    current_epoch: Optional[int] = None
    total_epochs: Optional[int] = None
    progress_percentage: float = 0.0
    current_phase: str = "queued"
    phase_message: str = ""
    eta_seconds: Optional[float] = None
    last_metrics: Optional[Dict[str, float]] = None


class RunArtifactsResponse(BaseModel):
    """Response model for run artifacts."""
    checkpoint_url: Optional[str] = None
    report_url: Optional[str] = None
    logs_url: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check."""
    ok: bool
    version: str = "1.0.0"
    uptime_s: int
    queue_stats: Optional[Dict[str, int]] = None


# Global state
app_start_time = time.time()
config = get_config()
run_store = get_run_store()
job_queue = get_job_queue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting DPO microservice")
    
    # Start job queue
    await job_queue.start()
    
    # Start service registration
    await start_registration()
    
    yield
    
    logger.info("Shutting down DPO microservice")
    
    # Stop service registration
    await stop_registration()
    
    # Stop job queue
    await job_queue.stop()


# Initialize FastAPI app
app = FastAPI(
    title="DPO Microservice",
    description="Direct Preference Optimization microservice with gateway integration",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
if config.allow_direct_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allow_direct_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    logger.info(f"CORS enabled for origins: {config.allow_direct_origins}")


# Rate limiting state (simple in-memory implementation)
rate_limit_state: Dict[str, List[float]] = {}


def check_rate_limit(uid: str) -> bool:
    """Check if user has exceeded rate limit."""
    # TEMPORARILY DISABLED FOR TESTING - RE-ENABLE IN PRODUCTION
    return True  # Allow all requests during testing
    # Original code commented out:
    now = time.time()
    window_start = now - 60  # 1 minute window
    
    # Clean up old entries and check current count
    user_requests = rate_limit_state.get(uid, [])
    user_requests = [req_time for req_time in user_requests if req_time > window_start]
    
    if len(user_requests) >= config.rate_limit_per_minute:
        return False
    
    # Record this request
    user_requests.append(now)
    rate_limit_state[uid] = user_requests
    return True


# API Endpoints

@app.get("/health", response_model=HealthResponse)
@app.get("/api/dpo/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns service health status and basic metrics.
    Available at both /health and /api/dpo/health for frontend compatibility.
    """
    try:
        uptime = int(time.time() - app_start_time)
        queue_stats = await run_store.get_queue_stats()
        queue_stats["queue_size"] = await job_queue.get_queue_size()
        queue_stats["active_jobs"] = await job_queue.get_active_job_count()
        
        return HealthResponse(
            ok=True,
            uptime_s=uptime,
            queue_stats=queue_stats
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


async def get_admin_user(request: Request) -> UserClaims:
    """Dependency to get authenticated admin user."""
    return await verify_request_auth(request, require_admin=True)

async def get_authenticated_user(request: Request) -> UserClaims:
    """Dependency to get authenticated user (admin not required)."""
    return await verify_request_auth(request, require_admin=False)

@app.post("/trigger-finetune", response_model=TriggerFinetuneResponse)
async def trigger_finetune(
    request: Request,
    data: TriggerFinetuneRequest,
    user: UserClaims = Depends(get_admin_user)
):
    """
    Trigger a fine-tuning job.
    
    Requires admin privileges (admin:true in gateway claims) and valid HMAC signature.
    
    Returns:
        - 200: Job successfully queued 
        - 401: Invalid/missing HMAC signature or malformed user claims
        - 403: Valid HMAC but admin=false (admin privileges required)
        - 429: Rate limit exceeded or active job exists for kb_id
    """
    logger.info(f"Finetune request from user {user.uid} for kb_id {data.kb_id}")
    
    # Rate limiting
    if not check_rate_limit(user.uid):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {config.rate_limit_per_minute} requests per minute."
        )
    
    # Check for active runs on same kb_id
    active_runs = await run_store.count_active_runs_for_kb(user.uid, data.kb_id)
    if active_runs > 0:
        raise HTTPException(
            status_code=429,
            detail=f"Active training already running for kb_id {data.kb_id}. Please wait for completion."
        )
    
    # Validate dataset size if inline
    if data.dataset_inline:
        if len(data.dataset_inline) == 0:
            raise HTTPException(status_code=400, detail="Inline dataset cannot be empty")
        
        # Rough size check (assume ~1KB per record)
        estimated_size_mb = len(data.dataset_inline) * 1024 / (1024 * 1024)
        if estimated_size_mb > config.max_dataset_size_mb:
            raise HTTPException(
                status_code=413,
                detail=f"Dataset too large: ~{estimated_size_mb:.1f}MB > {config.max_dataset_size_mb}MB"
            )
    
    try:
        # Create training run
        run = await run_store.create_run(
            uid=user.uid,
            kb_id=data.kb_id,
            exp_name=data.exp_name,
            base_model=data.base_model,
            algo=data.algo
        )
        
        # Create job request
        job = JobRequest(
            run_id=run.run_id,
            kb_id=data.kb_id,
            base_model=data.base_model,
            algo=data.algo,
            exp_name=data.exp_name,
            dataset_inline=[record.dict() for record in data.dataset_inline] if data.dataset_inline else None,
            dataset_url=data.dataset_url,
            idempotency_key=request.headers.get("Idempotency-Key")
        )
        
        # Submit to queue
        await job_queue.submit_job(job)
        
        logger.info(f"Created and queued training run {run.run_id}")
        
        return TriggerFinetuneResponse(
            run_id=run.run_id,
            status="queued"
        )
        
    except Exception as e:
        logger.error(f"Failed to create training run: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create training run: {str(e)}")


@app.get("/runs/{run_id}", response_model=RunStatusResponse)
async def get_run_status(
    run_id: str,
    user: UserClaims = Depends(get_authenticated_user)
):
    """
    Get status of a training run.
    
    Users can only access their own runs unless they are admin.
    Status will be one of: "queued", "running", "completed", "failed", "cancelled".
    
    Returns:
        - 200: Run status retrieved successfully
        - 401: Invalid/missing HMAC signature
        - 403: Valid HMAC but user cannot access this run
        - 404: Run not found
    """
    run = await run_store.get_run(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Check ownership or admin access
    if run.uid != user.uid and not user.admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return RunStatusResponse(
        run_id=run.run_id,
        status=run.status.value,
        metrics=run.metrics,
        started_at=int(run.started_at) if run.started_at else None,
        finished_at=int(run.finished_at) if run.finished_at else None,
        # Progress tracking fields
        current_step=run.current_step,
        total_steps=run.total_steps,
        current_epoch=run.current_epoch,
        total_epochs=run.total_epochs,
        progress_percentage=run.progress_percentage,
        current_phase=run.current_phase,
        phase_message=run.phase_message,
        eta_seconds=run.eta_seconds,
        last_metrics=run.last_metrics
    )


@app.get("/runs/{run_id}/artifacts", response_model=RunArtifactsResponse)  
async def get_run_artifacts(
    run_id: str,
    user: UserClaims = Depends(get_authenticated_user)
):
    """
    Get artifacts for a training run.
    
    Users can only access their own runs unless they are admin.
    """
    run = await run_store.get_run(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Check ownership or admin access
    if run.uid != user.uid and not user.admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return RunArtifactsResponse(
        checkpoint_url=run.checkpoint_url,
        report_url=run.report_url,
        logs_url=run.logs_url
    )


@app.delete("/runs/{run_id}")
async def cancel_run(
    run_id: str,
    user: UserClaims = Depends(get_authenticated_user)
):
    """
    Cancel a training run.
    
    Users can only cancel their own runs unless they are admin.
    """
    run = await run_store.get_run(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Check ownership or admin access
    if run.uid != user.uid and not user.admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if run can be cancelled
    if run.status not in [RunStatus.QUEUED, RunStatus.RUNNING]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel run with status {run.status}"
        )
    
    # Cancel the job
    cancelled = await job_queue.cancel_job(run_id)
    
    if cancelled:
        return {"status": "cancelled"}
    else:
        raise HTTPException(status_code=500, detail="Failed to cancel run")


# Development/debugging endpoints (only when direct origins are allowed)
if config.allow_direct_origins:
    
    @app.get("/debug/runs")
    async def list_all_runs():
        """Debug endpoint to list all runs."""
        stats = await run_store.get_queue_stats()
        return {
            "queue_stats": stats,
            "queue_size": await job_queue.get_queue_size(),
            "active_jobs": await job_queue.get_active_job_count()
        }


if __name__ == "__main__":
    uvicorn.run(
        "webhook_handler:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )