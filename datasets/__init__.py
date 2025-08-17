"""
Dataset interface abstractions for DPO Microservice.

This module defines the interface contracts that all preference datasets
must implement, ensuring consistency across different dataset implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Union, Any, Optional, Iterator
import json


class PreferenceDatasetInterface(ABC):
    """
    Abstract interface for preference datasets used in DPO training.
    
    All preference datasets must implement this interface to ensure
    compatibility with the training pipeline.
    """
    
    @abstractmethod
    def load_data(self, split: str = "train", **kwargs) -> Dict[str, Dict[str, Union[List[Tuple[int, int]], List[str], str]]]:
        """
        Load preference data for a specific split.
        
        Args:
            split: Dataset split to load ('train', 'test', 'validation')
            **kwargs: Additional dataset-specific arguments
            
        Returns:
            Dictionary with the following structure:
            {
                'prompt1': {
                    'responses': List[str],          # List of response options
                    'pairs': List[Tuple[int, int]],  # Preference pairs (chosen_idx, rejected_idx)
                    'sft_target': str                # Target response for SFT
                },
                'prompt2': {
                    ...
                },
            }
            
        Raises:
            ValueError: If dataset cannot be loaded or is malformed
        """
        pass
    
    @abstractmethod
    def validate_format(self, data: Dict[str, Any]) -> bool:
        """
        Validate that data conforms to the expected preference dataset format.
        
        Args:
            data: Data to validate
            
        Returns:
            True if data is valid, False otherwise
            
        Raises:
            ValueError: If data format is invalid with details about the issue
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this dataset."""
        pass
    
    @property
    @abstractmethod
    def supported_splits(self) -> List[str]:
        """Return list of supported dataset splits."""
        pass


class NovaltoDataset(PreferenceDatasetInterface):
    """
    Implementation for the Novalto preference dataset format.
    
    This dataset reads from a JSON file in the data directory and converts
    it to the standard preference dataset format used by the training pipeline.
    """
    
    def __init__(self, data_path: str = "data/dataset.json"):
        """
        Initialize the Novalto dataset.
        
        Args:
            data_path: Path to the dataset JSON file
        """
        self.data_path = data_path
    
    @property
    def name(self) -> str:
        """Return the name of this dataset."""
        return "novalto"
    
    @property
    def supported_splits(self) -> List[str]:
        """Return list of supported dataset splits."""
        return ["train"]  # Novalto dataset only supports training split
    
    def load_data(self, split: str = "train", **kwargs) -> Dict[str, Dict[str, Union[List[Tuple[int, int]], List[str], str]]]:
        """
        Load preference data from the Novalto JSON file.
        
        Args:
            split: Dataset split to load (only 'train' is supported)
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Dictionary in the standard preference dataset format
            
        Raises:
            ValueError: If dataset file is not found or malformed
        """
        if split not in self.supported_splits:
            raise ValueError(f"Unsupported split '{split}'. Supported splits: {self.supported_splits}")
        
        try:
            with open(self.data_path, "r") as f:
                raw_data = json.load(f)
        except FileNotFoundError:
            raise ValueError(f"Dataset file not found: {self.data_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in dataset file {self.data_path}: {e}")
        
        # Validate the raw data format
        if not self.validate_format(raw_data):
            raise ValueError(f"Dataset file {self.data_path} does not conform to expected format")
        
        # Convert to standard format
        processed_data = {}
        for entry in raw_data:
            prompt = entry["prompt"]
            processed_data[prompt] = {
                "responses": entry["responses"],
                "pairs": [tuple(pair) for pair in entry["pairs"]],  # Ensure tuples
                "sft_target": entry["sft_target"]
            }
        
        return processed_data
    
    def validate_format(self, data: Dict[str, Any]) -> bool:
        """
        Validate that data conforms to the Novalto dataset format.
        
        Expected format:
        [
            {
                "prompt": "Human: ... Assistant:",
                "responses": ["response1", "response2", ...],
                "pairs": [[chosen_idx, rejected_idx], ...],
                "sft_target": "target_response"
            },
            ...
        ]
        
        Args:
            data: Data to validate
            
        Returns:
            True if data is valid
            
        Raises:
            ValueError: If data format is invalid with details
        """
        if not isinstance(data, list):
            raise ValueError("Dataset must be a list of entries")
        
        if len(data) == 0:
            raise ValueError("Dataset cannot be empty")
        
        required_fields = {"prompt", "responses", "pairs", "sft_target"}
        
        for i, entry in enumerate(data):
            if not isinstance(entry, dict):
                raise ValueError(f"Entry {i} must be a dictionary")
            
            # Check required fields
            missing_fields = required_fields - set(entry.keys())
            if missing_fields:
                raise ValueError(f"Entry {i} missing required fields: {missing_fields}")
            
            # Validate field types
            if not isinstance(entry["prompt"], str):
                raise ValueError(f"Entry {i}: 'prompt' must be a string")
            
            if not isinstance(entry["responses"], list):
                raise ValueError(f"Entry {i}: 'responses' must be a list")
            
            if len(entry["responses"]) == 0:
                raise ValueError(f"Entry {i}: 'responses' cannot be empty")
            
            for j, response in enumerate(entry["responses"]):
                if not isinstance(response, str):
                    raise ValueError(f"Entry {i}, response {j}: must be a string")
            
            if not isinstance(entry["pairs"], list):
                raise ValueError(f"Entry {i}: 'pairs' must be a list")
            
            for j, pair in enumerate(entry["pairs"]):
                if not isinstance(pair, list) or len(pair) != 2:
                    raise ValueError(f"Entry {i}, pair {j}: must be a list of length 2")
                
                chosen_idx, rejected_idx = pair
                if not isinstance(chosen_idx, int) or not isinstance(rejected_idx, int):
                    raise ValueError(f"Entry {i}, pair {j}: indices must be integers")
                
                if chosen_idx < 0 or chosen_idx >= len(entry["responses"]):
                    raise ValueError(f"Entry {i}, pair {j}: chosen_idx {chosen_idx} out of range")
                
                if rejected_idx < 0 or rejected_idx >= len(entry["responses"]):
                    raise ValueError(f"Entry {i}, pair {j}: rejected_idx {rejected_idx} out of range")
                
                if chosen_idx == rejected_idx:
                    raise ValueError(f"Entry {i}, pair {j}: chosen and rejected indices cannot be the same")
            
            if not isinstance(entry["sft_target"], str):
                raise ValueError(f"Entry {i}: 'sft_target' must be a string")
            
            # Validate that sft_target is one of the responses
            if entry["sft_target"] not in entry["responses"]:
                raise ValueError(f"Entry {i}: 'sft_target' must be one of the responses")
        
        return True


# Registry of available dataset implementations
DATASET_REGISTRY = {
    "novalto": NovaltoDataset
}


def get_dataset_implementation(name: str, **kwargs) -> PreferenceDatasetInterface:
    """
    Get a dataset implementation by name.
    
    Args:
        name: Name of the dataset implementation
        **kwargs: Arguments to pass to the dataset constructor
        
    Returns:
        Dataset implementation instance
        
    Raises:
        ValueError: If dataset name is not found in registry
    """
    if name not in DATASET_REGISTRY:
        available = ", ".join(DATASET_REGISTRY.keys())
        raise ValueError(f"Unknown dataset '{name}'. Available datasets: {available}")
    
    dataset_class = DATASET_REGISTRY[name]
    return dataset_class(**kwargs)


def validate_dataset_file(file_path: str, dataset_type: str = "novalto") -> bool:
    """
    Validate a dataset file against the specified format.
    
    Args:
        file_path: Path to the dataset file
        dataset_type: Type of dataset format to validate against
        
    Returns:
        True if dataset is valid
        
    Raises:
        ValueError: If dataset is invalid with details
    """
    dataset = get_dataset_implementation(dataset_type, data_path=file_path)
    
    # Load and validate the data
    try:
        data = dataset.load_data()
        return True
    except Exception as e:
        raise ValueError(f"Dataset validation failed: {e}")


# Export the interface and main implementations
__all__ = [
    "PreferenceDatasetInterface",
    "NovaltoDataset", 
    "DATASET_REGISTRY",
    "get_dataset_implementation",
    "validate_dataset_file"
]