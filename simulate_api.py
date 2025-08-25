#!/usr/bin/env python3
"""
API Simulation Tool for DPO Microservice

This script simulates API calls to the DPO microservice for debugging and troubleshooting
fine-tuning issues without needing to establish server connections.

Usage:
    # Direct training mode (calls run_training directly)
    python simulate_api.py direct --dataset sample_data.json --exp-name test-experiment

    # Pipeline mode (simulates full job queue processing)
    python simulate_api.py pipeline --dataset sample_data.json --exp-name test-experiment

    # Create sample dataset
    python simulate_api.py create-sample --output sample_data.json
"""

import argparse
import json
import logging
import os
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import asyncio
from dataclasses import dataclass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Mock classes for pipeline simulation
@dataclass
class MockUserClaims:
    """Mock user claims for simulation."""
    uid: str = "sim_user"
    admin: bool = True


@dataclass
class MockJobRequest:
    """Mock job request matching the real JobRequest structure."""
    run_id: str
    kb_id: str
    base_model: str
    algo: str
    exp_name: str
    dataset_inline: Optional[List[Dict[str, Any]]] = None
    dataset_url: Optional[str] = None
    idempotency_key: Optional[str] = None


def create_sample_dataset(output_path: str, num_samples: int = 5):
    """Create a sample DPO dataset for testing."""
    sample_data = []
    
    for i in range(num_samples):
        sample_data.append({
            "prompt": f"What is the best way to learn programming? (Example {i+1})",
            "responses": [
                f"Start with Python as it's beginner-friendly and has great community support. Build small projects to practice. (Response A, Example {i+1})",
                f"Just dive into any language and start coding immediately without learning fundamentals. (Response B, Example {i+1})"
            ],
            "pairs": [[0, 1]],  # First response is preferred over second
            "sft_target": f"Start with Python as it's beginner-friendly and has great community support. Build small projects to practice. (SFT Target, Example {i+1})"
        })
    
    with open(output_path, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    logger.info(f"Created sample dataset with {num_samples} records at {output_path}")


def validate_dataset(dataset_path: str) -> List[Dict[str, Any]]:
    """Validate and load dataset from file."""
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
    
    with open(dataset_path, 'r') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError("Dataset must be a list of DPO records")
    
    if len(data) == 0:
        raise ValueError("Dataset cannot be empty")
    
    # Validate each record
    for i, record in enumerate(data):
        required_fields = ['prompt', 'responses', 'pairs', 'sft_target']
        for field in required_fields:
            if field not in record:
                raise ValueError(f"Record {i} missing required field: {field}")
        
        if not isinstance(record['responses'], list) or len(record['responses']) < 2:
            raise ValueError(f"Record {i} must have at least 2 responses")
        
        if not isinstance(record['pairs'], list) or len(record['pairs']) == 0:
            raise ValueError(f"Record {i} must have at least 1 preference pair")
    
    logger.info(f"Validated dataset with {len(data)} records")
    return data


def simulate_direct_training(
    dataset_path: str,
    exp_name: str,
    base_model: str = "zephyr",
    algo: str = "dpo",
    batch_size: int = 8,
    n_examples: int = 80,
    debug: bool = True
) -> Dict[str, str]:
    """
    Simulate direct training by calling run_training() directly.
    This bypasses all the web/queue infrastructure.
    """
    logger.info("=== DIRECT TRAINING SIMULATION ===")
    logger.info(f"Dataset: {dataset_path}")
    logger.info(f"Experiment: {exp_name}")
    logger.info(f"Model: {base_model}, Algorithm: {algo}")
    
    try:
        # Validate dataset
        dataset = validate_dataset(dataset_path)
        logger.info(f"Dataset validation passed: {len(dataset)} records")
        
        # Prepare dataset in expected location
        os.makedirs("data", exist_ok=True)
        dataset_target = "data/dataset.json"
        
        with open(dataset_target, 'w') as f:
            json.dump(dataset, f)
        logger.info(f"Dataset prepared at {dataset_target}")
        
        # Import and call training function
        try:
            from training import run_training
        except ImportError as e:
            logger.error(f"Failed to import training module: {e}")
            logger.error("Make sure you're running from the correct directory and dependencies are installed")
            raise
        
        # Validate batch size configuration  
        if batch_size < 4:
            logger.warning(f"Batch size {batch_size} is very small. DPO training works best with batch_size >= 16")
        if n_examples < batch_size * 2:
            logger.warning(f"n_examples ({n_examples}) should be at least 2x batch_size ({batch_size}) for stable training")
        
        logger.info("Starting direct training...")
        result = run_training(
            model_name=base_model,
            datasets=["novalto"],  # Uses the dataset.json we prepared
            loss_config={"name": algo, "beta": 0.1},
            exp_name=exp_name,
            debug=debug,
            batch_size=max(16, batch_size),  # Ensure minimum batch size
            eval_batch_size=4,
            n_examples=max(32, n_examples),  # Ensure minimum examples
            n_eval_examples=20
        )
        
        logger.info("✅ Direct training completed successfully!")
        logger.info(f"Artifact path: {result['artifact_path']}")
        logger.info(f"Logs path: {result['logs_path']}")
        
        return result
        
    except Exception as e:
        logger.error("❌ Direct training failed!")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise
    
    finally:
        # Cleanup
        if os.path.exists("data/dataset.json"):
            os.remove("data/dataset.json")
            logger.info("Cleaned up temporary dataset file")


async def simulate_pipeline_mode(
    dataset_path: str,
    exp_name: str,
    base_model: str = "zephyr",
    algo: str = "dpo",
    batch_size: int = 8,
    n_examples: int = 80,
    kb_id: str = "test_kb"
) -> Dict[str, Any]:
    """
    Simulate the full pipeline including job queue processing.
    This tests the same code path as a real API call but without HTTP/auth.
    """
    logger.info("=== PIPELINE SIMULATION ===")
    logger.info(f"Dataset: {dataset_path}")
    logger.info(f"Experiment: {exp_name}")
    logger.info(f"Model: {base_model}, Algorithm: {algo}")
    
    try:
        # Validate dataset
        dataset = validate_dataset(dataset_path)
        logger.info(f"Dataset validation passed: {len(dataset)} records")
        
        # Import required classes
        from core.run_store import get_run_store
        from core.job_queue import JobRequest
        
        # Create mock run
        run_store = get_run_store()
        user = MockUserClaims()
        
        logger.info("Creating training run...")
        run = await run_store.create_run(
            uid=user.uid,
            kb_id=kb_id,
            exp_name=exp_name,
            base_model=base_model,
            algo=algo
        )
        logger.info(f"Created run: {run.run_id}")
        
        # Create job request
        job = JobRequest(
            run_id=run.run_id,
            kb_id=kb_id,
            base_model=base_model,
            algo=algo,
            exp_name=exp_name,
            dataset_inline=dataset,
            dataset_url=None,
            idempotency_key=None
        )
        
        # Simulate job processing directly (bypass queue)
        logger.info("Processing job...")
        await simulate_job_processing(job, run_store)
        
        # Get final run status
        final_run = await run_store.get_run(run.run_id)
        
        result = {
            "run_id": run.run_id,
            "status": final_run.status.value if final_run else "unknown",
            "artifact_path": final_run.checkpoint_url if final_run else None,
            "logs_path": final_run.logs_url if final_run else None
        }
        
        logger.info("✅ Pipeline simulation completed!")
        logger.info(f"Final status: {result['status']}")
        
        return result
        
    except Exception as e:
        logger.error("❌ Pipeline simulation failed!")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise


async def simulate_job_processing(job: MockJobRequest, run_store):
    """Simulate the job processing logic from JobQueue._process_job()"""
    from core.run_store import RunStatus
    
    run_id = job.run_id
    
    try:
        # Update status to running
        logger.info(f"Updating run {run_id} to RUNNING")
        await run_store.update_run_status(run_id, RunStatus.RUNNING)
        
        # Prepare dataset
        dataset_path = await prepare_dataset_for_job(job)
        logger.info(f"Dataset prepared at: {dataset_path}")
        
        try:
            # Import training module
            from training import run_training
            
            # Model mapping (same as in JobQueue)
            model_mapping = {
                "pythia_2_8b": "pythia28",
                "pythia_6_9b": "pythia69", 
                "pythia-2.8b": "pythia28",
                "pythia-6.9b": "pythia69",
                "zephyr": "zephyr",
                "gpt2": "gpt2-large",
                "llama": "llama7b"
            }
            
            mapped_model = model_mapping.get(job.base_model, "zephyr")
            logger.info(f"Using model '{mapped_model}' for requested '{job.base_model}'")
            
            # Validate batch size configuration
            if job.batch_size < 4:
                logger.warning(f"Batch size {job.batch_size} is very small. DPO training works best with batch_size >= 16")
            
            # Run training
            logger.info("Starting training execution...")
            result = run_training(
                model_name=mapped_model,
                datasets=["novalto"],  # Always use novalto for microservice
                loss_config={"name": job.algo, "beta": 0.1},
                exp_name=job.exp_name,
                debug=True,  # Disable wandb
                batch_size=max(16, job.batch_size),  # Ensure minimum batch size
                eval_batch_size=4,
                n_examples=max(32, job.n_examples),  # Ensure minimum examples
                n_eval_examples=20
            )
            
            # Update run with results
            await run_store.update_run_artifacts(
                run_id,
                checkpoint_url=result["artifact_path"],
                logs_url=result["logs_path"]
            )
            
            # Mark as completed
            await run_store.update_run_status(run_id, RunStatus.COMPLETED)
            logger.info(f"Job {run_id} completed successfully")
            
        finally:
            # Clean up dataset file
            if os.path.exists(dataset_path):
                os.remove(dataset_path)
                logger.info("Cleaned up temporary dataset file")
                
    except Exception as e:
        # Job failed
        error_msg = str(e)
        await run_store.update_run_status(run_id, RunStatus.FAILED, error_msg)
        logger.error(f"Job {run_id} failed: {error_msg}")
        raise


async def prepare_dataset_for_job(job: MockJobRequest) -> str:
    """Prepare dataset file for training (same logic as JobQueue._prepare_dataset)"""
    # Create data directory
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    
    # Use standard dataset.json name
    dataset_path = os.path.join(data_dir, "dataset.json")
    
    if job.dataset_inline:
        # Use inline dataset
        with open(dataset_path, "w") as f:
            json.dump(job.dataset_inline, f)
    else:
        raise ValueError("No dataset provided")
    
    return dataset_path


def main():
    parser = argparse.ArgumentParser(description="API Simulation Tool for DPO Microservice")
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    subparsers = parser.add_subparsers(dest='mode', help='Simulation mode')
    
    # Direct mode
    direct_parser = subparsers.add_parser('direct', help='Direct training simulation')
    direct_parser.add_argument('--dataset', required=True, help='Path to dataset JSON file')
    direct_parser.add_argument('--exp-name', required=True, help='Experiment name')
    direct_parser.add_argument('--model', default='zephyr', help='Base model (default: zephyr)')
    direct_parser.add_argument('--algo', default='dpo', help='Training algorithm (default: dpo)')
    direct_parser.add_argument('--batch-size', type=int, default=16, help='Batch size (default: 16)')
    direct_parser.add_argument('--n-examples', type=int, default=100, help='Number of examples (default: 100)')
    
    # Pipeline mode
    pipeline_parser = subparsers.add_parser('pipeline', help='Full pipeline simulation')
    pipeline_parser.add_argument('--dataset', required=True, help='Path to dataset JSON file')
    pipeline_parser.add_argument('--exp-name', required=True, help='Experiment name')
    pipeline_parser.add_argument('--model', default='zephyr', help='Base model (default: zephyr)')
    pipeline_parser.add_argument('--algo', default='dpo', help='Training algorithm (default: dpo)')
    pipeline_parser.add_argument('--batch-size', type=int, default=16, help='Batch size (default: 16)')
    pipeline_parser.add_argument('--n-examples', type=int, default=100, help='Number of examples (default: 100)')
    pipeline_parser.add_argument('--kb-id', default='test_kb', help='Knowledge base ID (default: test_kb)')
    
    # Create sample
    sample_parser = subparsers.add_parser('create-sample', help='Create sample dataset')
    sample_parser.add_argument('--output', required=True, help='Output file path')
    sample_parser.add_argument('--num-samples', type=int, default=5, help='Number of samples (default: 5)')
    
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not args.mode:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.mode == 'create-sample':
            create_sample_dataset(args.output, args.num_samples)
            
        elif args.mode == 'direct':
            result = simulate_direct_training(
                dataset_path=args.dataset,
                exp_name=args.exp_name,
                base_model=args.model,
                algo=args.algo,
                batch_size=args.batch_size,
                n_examples=args.n_examples
            )
            print("\n✅ SIMULATION COMPLETED SUCCESSFULLY!")
            print(f"Artifact: {result['artifact_path']}")
            print(f"Logs: {result['logs_path']}")
            
        elif args.mode == 'pipeline':
            result = asyncio.run(simulate_pipeline_mode(
                dataset_path=args.dataset,
                exp_name=args.exp_name,
                base_model=args.model,
                algo=args.algo,
                kb_id=args.kb_id
            ))
            print("\n✅ SIMULATION COMPLETED SUCCESSFULLY!")
            print(f"Run ID: {result['run_id']}")
            print(f"Status: {result['status']}")
            print(f"Artifact: {result['artifact_path']}")
            print(f"Logs: {result['logs_path']}")
            
    except Exception as e:
        print(f"\n❌ SIMULATION FAILED: {str(e)}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()