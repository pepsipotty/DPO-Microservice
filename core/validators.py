"""
Configuration validation utilities for DPO Microservice.

This module provides validation functions for Hydra configurations,
ensuring that all configuration files conform to expected schemas.
"""

import os
import yaml
import jsonschema
from pathlib import Path
from typing import Dict, Any, Optional, Union
from omegaconf import OmegaConf, DictConfig


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


def load_yaml_schema(schema_path: str) -> Dict[str, Any]:
    """
    Load a YAML schema file.
    
    Args:
        schema_path: Path to the schema YAML file
        
    Returns:
        Dictionary containing the schema
        
    Raises:
        ConfigValidationError: If schema file cannot be loaded
    """
    try:
        with open(schema_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigValidationError(f"Schema file not found: {schema_path}")
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Invalid YAML in schema file {schema_path}: {e}")


def validate_config_against_schema(config: Dict[str, Any], schema: Dict[str, Any], config_name: str = "config") -> None:
    """
    Validate a configuration dictionary against a JSON schema.
    
    Args:
        config: Configuration dictionary to validate
        schema: JSON schema dictionary
        config_name: Name of the configuration for error messages
        
    Raises:
        ConfigValidationError: If validation fails
    """
    try:
        jsonschema.validate(instance=config, schema=schema)
    except jsonschema.ValidationError as e:
        raise ConfigValidationError(f"Validation failed for {config_name}: {e.message}")
    except jsonschema.SchemaError as e:
        raise ConfigValidationError(f"Invalid schema for {config_name}: {e.message}")


def validate_training_config(config_path: str) -> Dict[str, Any]:
    """
    Validate a training configuration file against the training schema.
    
    Args:
        config_path: Path to the configuration YAML file
        
    Returns:
        The loaded and validated configuration
        
    Raises:
        ConfigValidationError: If validation fails
    """
    # Determine the project root directory
    current_dir = Path(__file__).parent.parent
    schema_path = current_dir / "config" / "schemas" / "training_schema.yaml"
    
    # Load schema
    schema = load_yaml_schema(str(schema_path))
    
    # Load configuration
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigValidationError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Invalid YAML in configuration file {config_path}: {e}")
    
    # Validate
    validate_config_against_schema(config, schema, "training_config")
    
    return config


def validate_model_config(config_path: str) -> Dict[str, Any]:
    """
    Validate a model configuration file against the model schema.
    
    Args:
        config_path: Path to the model configuration YAML file
        
    Returns:
        The loaded and validated configuration
        
    Raises:
        ConfigValidationError: If validation fails
    """
    # Determine the project root directory
    current_dir = Path(__file__).parent.parent
    schema_path = current_dir / "config" / "schemas" / "model_schema.yaml"
    
    # Load schema
    schema = load_yaml_schema(str(schema_path))
    
    # Load configuration
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigValidationError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Invalid YAML in configuration file {config_path}: {e}")
    
    # Validate
    validate_config_against_schema(config, schema, "model_config")
    
    return config


def validate_loss_config(config_path: str) -> Dict[str, Any]:
    """
    Validate a loss configuration file against the loss schema.
    
    Args:
        config_path: Path to the loss configuration YAML file
        
    Returns:
        The loaded and validated configuration
        
    Raises:
        ConfigValidationError: If validation fails
    """
    # Determine the project root directory
    current_dir = Path(__file__).parent.parent
    schema_path = current_dir / "config" / "schemas" / "loss_schema.yaml"
    
    # Load schema
    schema = load_yaml_schema(str(schema_path))
    
    # Load configuration
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigValidationError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Invalid YAML in configuration file {config_path}: {e}")
    
    # Validate
    validate_config_against_schema(config, schema, "loss_config")
    
    return config


def validate_hydra_config(config_name: str = "config", config_path: str = "config") -> DictConfig:
    """
    Validate a complete Hydra configuration by loading it and checking all components.
    
    Args:
        config_name: Name of the main configuration file (without .yaml extension)
        config_path: Path to the configuration directory
        
    Returns:
        The loaded and validated Hydra configuration
        
    Raises:
        ConfigValidationError: If validation fails
    """
    try:
        from hydra import initialize, compose
        from hydra.core.global_hydra import GlobalHydra
        
        # Clear any existing Hydra instance
        GlobalHydra.instance().clear()
        
        # Initialize Hydra and compose configuration
        with initialize(config_path=config_path, version_base=None):
            cfg = compose(config_name=config_name)
            
        # Convert to regular dict for validation
        config_dict = OmegaConf.to_container(cfg, resolve=True)
        
        # Validate main training configuration
        current_dir = Path(__file__).parent.parent
        training_schema_path = current_dir / "config" / "schemas" / "training_schema.yaml"
        training_schema = load_yaml_schema(str(training_schema_path))
        validate_config_against_schema(config_dict, training_schema, "hydra_config")
        
        return cfg
        
    except Exception as e:
        raise ConfigValidationError(f"Failed to validate Hydra configuration: {e}")


def validate_environment_variables() -> Dict[str, Optional[str]]:
    """
    Validate that required environment variables are set.
    
    Returns:
        Dictionary of environment variable names and their values
        
    Raises:
        ConfigValidationError: If required environment variables are missing
    """
    # Required environment variables
    required_vars = [
        "FIREBASE_SERVICE_KEY_PATH",
        "FIREBASE_STORAGE_BUCKET"
    ]
    
    # Optional but recommended environment variables
    optional_vars = [
        "WANDB_API_KEY",
        "WANDB_ENTITY",
        "WANDB_PROJECT",
        "WANDB_DISABLED",
        "CACHE_DIR",
        "HF_HOME",
        "DATASET_PATH"
    ]
    
    env_vars = {}
    missing_required = []
    
    # Check required variables
    for var in required_vars:
        value = os.environ.get(var)
        if value is None:
            missing_required.append(var)
        env_vars[var] = value
    
    # Check optional variables
    for var in optional_vars:
        env_vars[var] = os.environ.get(var)
    
    if missing_required:
        raise ConfigValidationError(
            f"Missing required environment variables: {', '.join(missing_required)}. "
            f"Please check .env.example for reference."
        )
    
    return env_vars


def validate_all_configs(config_dir: str = "config") -> Dict[str, Any]:
    """
    Validate all configuration files in the configuration directory.
    
    Args:
        config_dir: Path to the configuration directory
        
    Returns:
        Dictionary with validation results for each configuration type
        
    Raises:
        ConfigValidationError: If any validation fails
    """
    results = {}
    
    # Validate main training configuration
    try:
        main_config_path = os.path.join(config_dir, "config.yaml")
        results["training"] = validate_training_config(main_config_path)
    except Exception as e:
        raise ConfigValidationError(f"Training config validation failed: {e}")
    
    # Validate model configurations
    model_dir = os.path.join(config_dir, "model")
    if os.path.exists(model_dir):
        results["models"] = {}
        for model_file in os.listdir(model_dir):
            if model_file.endswith(".yaml"):
                model_name = model_file[:-5]  # Remove .yaml extension
                model_path = os.path.join(model_dir, model_file)
                try:
                    results["models"][model_name] = validate_model_config(model_path)
                except Exception as e:
                    raise ConfigValidationError(f"Model config '{model_name}' validation failed: {e}")
    
    # Validate loss configurations
    loss_dir = os.path.join(config_dir, "loss")
    if os.path.exists(loss_dir):
        results["losses"] = {}
        for loss_file in os.listdir(loss_dir):
            if loss_file.endswith(".yaml"):
                loss_name = loss_file[:-5]  # Remove .yaml extension
                loss_path = os.path.join(loss_dir, loss_file)
                try:
                    results["losses"][loss_name] = validate_loss_config(loss_path)
                except Exception as e:
                    raise ConfigValidationError(f"Loss config '{loss_name}' validation failed: {e}")
    
    # Validate environment variables
    try:
        results["environment"] = validate_environment_variables()
    except Exception as e:
        # Environment validation is non-fatal, just warn
        results["environment"] = {"warning": str(e)}
    
    return results