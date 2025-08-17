"""
Test suite for dataset interfaces and validation.

This module tests the dataset interface implementations, validation functions,
and the roundtrip process: toy data generation → dataset loading → validation.
"""

import json
import pytest
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List

# Add project root to Python path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datasets import (
    PreferenceDatasetInterface,
    NovaltoDataset,
    get_dataset_implementation,
    validate_dataset_file,
    DATASET_REGISTRY
)
from tools.make_toy_novalto import generate_toy_dataset


class TestPreferenceDatasetInterface:
    """Test the PreferenceDatasetInterface abstract class."""
    
    def test_interface_is_abstract(self):
        """Test that the interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PreferenceDatasetInterface()
    
    def test_interface_has_required_methods(self):
        """Test that the interface defines all required abstract methods."""
        required_methods = ['load_data', 'validate_format', 'name', 'supported_splits']
        
        for method in required_methods:
            assert hasattr(PreferenceDatasetInterface, method)
            assert callable(getattr(PreferenceDatasetInterface, method, None)) or isinstance(getattr(PreferenceDatasetInterface, method, None), property)


class TestNovaltoDataset:
    """Test the NovaltoDataset implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_path = os.path.join(self.temp_dir, "test_dataset.json")
        
        # Create a valid test dataset
        self.valid_dataset = [
            {
                "prompt": "\n\nHuman: What is 2+2?\n\nAssistant:",
                "responses": [
                    " 2+2 equals 4.",
                    " Two plus two is four.",
                    " The answer is 4."
                ],
                "pairs": [[0, 1], [2, 1]],
                "sft_target": " 2+2 equals 4."
            },
            {
                "prompt": "\n\nHuman: Name a color.\n\nAssistant:",
                "responses": [
                    " Blue is a nice color.",
                    " Red."
                ],
                "pairs": [[0, 1]],
                "sft_target": " Blue is a nice color."
            }
        ]
        
        with open(self.test_data_path, 'w') as f:
            json.dump(self.valid_dataset, f)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_dataset_properties(self):
        """Test dataset basic properties."""
        dataset = NovaltoDataset(self.test_data_path)
        
        assert dataset.name == "novalto"
        assert dataset.supported_splits == ["train"]
    
    def test_load_valid_data(self):
        """Test loading valid dataset."""
        dataset = NovaltoDataset(self.test_data_path)
        data = dataset.load_data("train")
        
        assert len(data) == 2
        
        # Check first entry
        first_prompt = "\n\nHuman: What is 2+2?\n\nAssistant:"
        assert first_prompt in data
        
        first_entry = data[first_prompt]
        assert len(first_entry["responses"]) == 3
        assert len(first_entry["pairs"]) == 2
        assert first_entry["sft_target"] == " 2+2 equals 4."
        
        # Check that pairs are tuples
        for pair in first_entry["pairs"]:
            assert isinstance(pair, tuple)
            assert len(pair) == 2
    
    def test_load_unsupported_split(self):
        """Test loading unsupported split raises error."""
        dataset = NovaltoDataset(self.test_data_path)
        
        with pytest.raises(ValueError, match="Unsupported split 'test'"):
            dataset.load_data("test")
    
    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises error."""
        dataset = NovaltoDataset("nonexistent.json")
        
        with pytest.raises(ValueError, match="Dataset file not found"):
            dataset.load_data()
    
    def test_load_invalid_json(self):
        """Test loading invalid JSON raises error."""
        invalid_json_path = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_json_path, 'w') as f:
            f.write("{ invalid json }")
        
        dataset = NovaltoDataset(invalid_json_path)
        
        with pytest.raises(ValueError, match="Invalid JSON"):
            dataset.load_data()
    
    def test_validate_format_valid_data(self):
        """Test validating correct format."""
        dataset = NovaltoDataset(self.test_data_path)
        
        assert dataset.validate_format(self.valid_dataset) is True
    
    def test_validate_format_not_list(self):
        """Test validation fails for non-list data."""
        dataset = NovaltoDataset(self.test_data_path)
        
        with pytest.raises(ValueError, match="Dataset must be a list"):
            dataset.validate_format({"not": "a list"})
    
    def test_validate_format_empty_list(self):
        """Test validation fails for empty dataset."""
        dataset = NovaltoDataset(self.test_data_path)
        
        with pytest.raises(ValueError, match="Dataset cannot be empty"):
            dataset.validate_format([])
    
    def test_validate_format_missing_fields(self):
        """Test validation fails for missing required fields."""
        dataset = NovaltoDataset(self.test_data_path)
        
        invalid_data = [{"prompt": "test"}]  # Missing other required fields
        
        with pytest.raises(ValueError, match="missing required fields"):
            dataset.validate_format(invalid_data)
    
    def test_validate_format_invalid_field_types(self):
        """Test validation fails for invalid field types."""
        dataset = NovaltoDataset(self.test_data_path)
        
        # Test invalid prompt type
        invalid_data = [{
            "prompt": 123,  # Should be string
            "responses": ["response"],
            "pairs": [[0, 1]],
            "sft_target": "response"
        }]
        
        with pytest.raises(ValueError, match="'prompt' must be a string"):
            dataset.validate_format(invalid_data)
    
    def test_validate_format_invalid_pairs(self):
        """Test validation fails for invalid preference pairs."""
        dataset = NovaltoDataset(self.test_data_path)
        
        # Test invalid pair indices
        invalid_data = [{
            "prompt": "\n\nHuman: Test\n\nAssistant:",
            "responses": ["response1", "response2"],
            "pairs": [[0, 5]],  # Index 5 is out of range
            "sft_target": "response1"
        }]
        
        with pytest.raises(ValueError, match="out of range"):
            dataset.validate_format(invalid_data)
    
    def test_validate_format_invalid_sft_target(self):
        """Test validation fails for invalid SFT target."""
        dataset = NovaltoDataset(self.test_data_path)
        
        # Test SFT target not in responses
        invalid_data = [{
            "prompt": "\n\nHuman: Test\n\nAssistant:",
            "responses": ["response1", "response2"],
            "pairs": [[0, 1]],
            "sft_target": "different response"  # Not in responses list
        }]
        
        with pytest.raises(ValueError, match="'sft_target' must be one of the responses"):
            dataset.validate_format(invalid_data)


class TestDatasetRegistry:
    """Test the dataset registry and factory functions."""
    
    def test_registry_contains_novalto(self):
        """Test that registry contains novalto dataset."""
        assert "novalto" in DATASET_REGISTRY
        assert DATASET_REGISTRY["novalto"] == NovaltoDataset
    
    def test_get_dataset_implementation_valid(self):
        """Test getting valid dataset implementation."""
        dataset = get_dataset_implementation("novalto", data_path="test.json")
        
        assert isinstance(dataset, NovaltoDataset)
        assert dataset.data_path == "test.json"
    
    def test_get_dataset_implementation_invalid(self):
        """Test getting invalid dataset implementation raises error."""
        with pytest.raises(ValueError, match="Unknown dataset 'invalid'"):
            get_dataset_implementation("invalid")


class TestDatasetValidation:
    """Test the dataset validation functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_path = os.path.join(self.temp_dir, "test_dataset.json")
        
        # Create a valid test dataset using the toy generator
        toy_data = generate_toy_dataset(3)
        with open(self.test_data_path, 'w') as f:
            json.dump(toy_data, f)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_validate_dataset_file_valid(self):
        """Test validating a valid dataset file."""
        is_valid = validate_dataset_file(self.test_data_path, "novalto")
        assert is_valid is True
    
    def test_validate_dataset_file_invalid_type(self):
        """Test validating with invalid dataset type."""
        with pytest.raises(ValueError, match="Unknown dataset 'invalid'"):
            validate_dataset_file(self.test_data_path, "invalid")
    
    def test_validate_dataset_file_nonexistent(self):
        """Test validating non-existent file."""
        with pytest.raises(ValueError, match="Dataset validation failed"):
            validate_dataset_file("nonexistent.json", "novalto")


class TestToyDatasetGeneration:
    """Test the toy dataset generation functionality."""
    
    def test_generate_toy_dataset(self):
        """Test generating toy dataset."""
        dataset = generate_toy_dataset(5)
        
        assert len(dataset) == 5
        assert isinstance(dataset, list)
        
        for entry in dataset:
            assert isinstance(entry, dict)
            assert "prompt" in entry
            assert "responses" in entry
            assert "pairs" in entry
            assert "sft_target" in entry
    
    def test_toy_dataset_validation(self):
        """Test that generated toy dataset passes validation."""
        dataset = generate_toy_dataset(3)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(dataset, f)
            temp_path = f.name
        
        try:
            # Validate the generated dataset
            is_valid = validate_dataset_file(temp_path, "novalto")
            assert is_valid is True
            
            # Also test with NovaltoDataset directly
            novalto_dataset = NovaltoDataset(temp_path)
            loaded_data = novalto_dataset.load_data()
            
            assert len(loaded_data) == 3
            
        finally:
            os.unlink(temp_path)


class TestDatasetRoundtrip:
    """Test the complete roundtrip: generation → loading → validation."""
    
    def test_roundtrip_process(self):
        """Test complete roundtrip process."""
        # Step 1: Generate toy dataset
        toy_data = generate_toy_dataset(5)
        
        # Step 2: Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(toy_data, f)
            temp_path = f.name
        
        try:
            # Step 3: Load through dataset interface
            dataset = NovaltoDataset(temp_path)
            loaded_data = dataset.load_data()
            
            # Step 4: Validate loaded data
            assert len(loaded_data) == 5
            
            for prompt, entry in loaded_data.items():
                assert isinstance(prompt, str)
                assert prompt.endswith("\n\nAssistant:")
                
                assert "responses" in entry
                assert "pairs" in entry
                assert "sft_target" in entry
                
                assert len(entry["responses"]) >= 2
                assert len(entry["pairs"]) >= 1
                assert entry["sft_target"] in entry["responses"]
            
            # Step 5: Validate using validation function
            is_valid = validate_dataset_file(temp_path, "novalto")
            assert is_valid is True
            
        finally:
            os.unlink(temp_path)
    
    def test_roundtrip_with_existing_dataset_loader(self):
        """Test roundtrip with the existing get_novalto_dataset function."""
        # Generate toy dataset
        toy_data = generate_toy_dataset(3)
        
        # Save to the expected location
        data_dir = Path(project_root) / "data"
        data_dir.mkdir(exist_ok=True)
        dataset_path = data_dir / "dataset.json"
        
        # Backup existing dataset if it exists
        backup_path = None
        if dataset_path.exists():
            backup_path = dataset_path.with_suffix(".json.backup")
            dataset_path.rename(backup_path)
        
        try:
            # Write toy dataset
            with open(dataset_path, 'w') as f:
                json.dump(toy_data, f)
            
            # Import and test the existing function
            from preference_datasets import get_novalto_dataset
            
            loaded_data = get_novalto_dataset()
            
            assert len(loaded_data) == 3
            
            # Verify structure matches expected format
            for prompt, entry in loaded_data.items():
                assert "responses" in entry
                assert "pairs" in entry
                assert "sft_target" in entry
                
                # Check that pairs are in correct format (tuples)
                for pair in entry["pairs"]:
                    assert isinstance(pair, tuple)
                    assert len(pair) == 2
                    assert isinstance(pair[0], int)
                    assert isinstance(pair[1], int)
        
        finally:
            # Clean up
            if dataset_path.exists():
                dataset_path.unlink()
            
            # Restore backup if it existed
            if backup_path and backup_path.exists():
                backup_path.rename(dataset_path)


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])