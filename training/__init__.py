"""
Training package for DPO microservice.

This package provides a clean programmatic interface to the DPO training system
while preserving exact training semantics and maintaining CLI compatibility.
"""

import os
import tempfile
import shutil
import json
from typing import Dict, List, Optional, Union, Any
from pathlib import Path


def run_training(
    model_name: str,
    datasets: Union[str, List[str]],
    loss_config: Dict[str, Any],
    exp_name: str,
    kb_id: Optional[str] = None,  # Add kb_id parameter for new naming convention
    trainer: str = "FSDPTrainer",
    batch_size: int = 128,
    eval_batch_size: int = 64,
    lr: float = 3e-6,
    n_epochs: Optional[int] = 1,
    n_examples: Optional[int] = None,
    n_eval_examples: int = 256,
    max_length: int = 512,
    max_prompt_length: int = 256,
    seed: int = 0,
    debug: bool = False,
    **kwargs
) -> Dict[str, str]:
    """
    Run DPO training with the specified configuration.
    
    This facade function maintains exact compatibility with the CLI interface
    while providing a clean programmatic API.
    
    Args:
        model_name: Name of the model configuration (e.g., 'zephyr', 'gpt2-large')
        datasets: Dataset name(s) to train on (e.g., 'novalto' or ['hh', 'shp'])
        loss_config: Loss configuration dict (e.g., {'name': 'dpo', 'beta': 0.1})
        exp_name: Experiment name for tracking and output directory
        kb_id: Knowledge base ID for new file naming convention (optional, falls back to exp_name)
        trainer: Trainer class to use ('BasicTrainer', 'FSDPTrainer', 'TensorParallelTrainer')
        batch_size: Training batch size
        eval_batch_size: Evaluation batch size
        lr: Learning rate
        n_epochs: Number of epochs (if None, must specify n_examples)
        n_examples: Number of examples (if None, must specify n_epochs)
        n_eval_examples: Number of examples for evaluation
        max_length: Maximum sequence length
        max_prompt_length: Maximum prompt length
        seed: Random seed
        debug: Enable debug mode (disables wandb, checkpointing)
        **kwargs: Additional configuration parameters
        
    Returns:
        Dict containing:
            - artifact_path: Path to the final policy.pt file
            - logs_path: Path to the experiment run directory
            - exp_name: The experiment name used
            
    Raises:
        ValueError: If configuration is invalid
        RuntimeError: If training fails
    """
    
    # Import heavy dependencies only when actually called
    try:
        import hydra
        from omegaconf import DictConfig, OmegaConf
        from .train import main as train_main
    except ImportError as e:
        raise RuntimeError(f"Training dependencies not available: {e}. Please install requirements.txt") from e
    
    # Ensure datasets is a list
    if isinstance(datasets, str):
        datasets = [datasets]
    
    # Create a temporary config override
    config_overrides = {
        'model': model_name,
        'datasets': datasets,
        'loss': loss_config,
        'exp_name': exp_name,
        'kb_id': kb_id,  # Add kb_id to config for new file naming
        'trainer': trainer,
        'batch_size': batch_size,
        'eval_batch_size': eval_batch_size,
        'lr': lr,
        'n_eval_examples': n_eval_examples,
        'max_length': max_length,
        'max_prompt_length': max_prompt_length,
        'seed': seed,
        'debug': debug,
    }
    
    if n_epochs is not None:
        config_overrides['n_epochs'] = n_epochs
        config_overrides['n_examples'] = None
    elif n_examples is not None:
        config_overrides['n_examples'] = n_examples
        config_overrides['n_epochs'] = None
    else:
        raise ValueError("Must specify either n_epochs or n_examples")
    
    # Add any additional kwargs
    config_overrides.update(kwargs)
    
    # Store original working directory
    original_cwd = os.getcwd()
    
    try:
        # Change to the package directory for Hydra to find configs
        package_dir = Path(__file__).parent.parent
        os.chdir(package_dir)
        
        # Initialize Hydra with our config
        config_dir = str(package_dir / "config")
        with hydra.initialize_config_dir(version_base=None, config_dir=config_dir):
            # Create config with overrides
            overrides = []
            for key, value in config_overrides.items():
                if isinstance(value, dict):
                    # Handle nested config like loss
                    for subkey, subvalue in value.items():
                        overrides.append(f"{key}.{subkey}={subvalue}")
                elif isinstance(value, list):
                    # Handle list values like datasets
                    if len(value) == 1:
                        overrides.append(f"{key}=[{value[0]}]")
                    else:
                        overrides.append(f"{key}=[{','.join(value)}]")
                else:
                    # Handle None values properly for Hydra
                    if value is None:
                        overrides.append(f"{key}=null")
                    else:
                        overrides.append(f"{key}={value}")
            
            cfg = hydra.compose(config_name="config", overrides=overrides)
            
            # Resolve the config to get the actual run directory
            OmegaConf.resolve(cfg)
            
            # Run training using the main function
            train_main(cfg)
            
            # Construct result paths
            run_dir = cfg.local_run_dir
            artifact_path = os.path.join(run_dir, "LATEST", "policy.pt")
            success_marker_path = os.path.join(run_dir, "LATEST", ".upload_success")
            
            # Check for upload success first (preferred)
            if os.path.exists(success_marker_path):
                # Upload was successful, read Firebase URL from marker file
                with open(success_marker_path, 'r') as f:
                    firebase_url = f.read().strip()
                
                return {
                    "artifact_path": firebase_url,  # Use Firebase URL instead of local path
                    "logs_path": os.path.abspath(run_dir),
                    "exp_name": exp_name
                }
            
            # Fallback: verify local artifact exists (for cases without upload)
            elif os.path.exists(artifact_path):
                return {
                    "artifact_path": os.path.abspath(artifact_path),
                    "logs_path": os.path.abspath(run_dir),
                    "exp_name": exp_name
                }
            
            else:
                # Neither upload success nor local file found
                raise RuntimeError(f"Training completed but no artifact found. Expected local file at {artifact_path} or upload success marker at {success_marker_path}")
            
    except Exception as e:
        raise RuntimeError(f"Training failed: {str(e)}") from e
    
    finally:
        # Restore original working directory
        os.chdir(original_cwd)


# For backward compatibility, define lazy imports for training components
def _lazy_import_trainers():
    """Lazy import of trainers module."""
    from . import trainers
    return trainers

def _lazy_import_train():
    """Lazy import of train module."""
    from .train import main as train_main, worker_main
    return train_main, worker_main

# Expose main facade function
__all__ = ['run_training']

# Note: trainers, train_main, worker_main are available via lazy imports if needed