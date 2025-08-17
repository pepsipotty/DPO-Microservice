"""
Comprehensive API integration tests for the DPO microservice webhook handler.

These tests verify the complete pipeline: API → Training → Storage integration.
"""

import pytest
import json
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from pathlib import Path

# Import the FastAPI app
from webhook_handler import app


class TestWebhookAPI:
    """Test suite for the webhook API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)

    @pytest.fixture
    def sample_dataset(self):
        """Sample dataset payload for testing."""
        return {
            "communityId": "test_community",
            "dataset": [
                {
                    "prompt": "What is the best programming language?",
                    "chosen": "Python is great for data science and machine learning due to its extensive libraries.",
                    "rejected": "Assembly is the only real programming language."
                },
                {
                    "prompt": "How do you train a neural network?",
                    "chosen": "Start with good data preprocessing, choose appropriate architecture, and tune hyperparameters carefully.",
                    "rejected": "Just throw more GPUs at it until it works."
                },
                {
                    "prompt": "What is reinforcement learning?",
                    "chosen": "A machine learning paradigm where agents learn through interaction with an environment.",
                    "rejected": "It's when you reward your computer with cookies."
                }
            ]
        }

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "dpo-microservice"

    @patch('webhook_handler.firebase_admin')
    def test_trigger_finetune_success_with_facade(self, mock_firebase, client, sample_dataset, temp_data_dir):
        """Test successful fine-tuning using the training facade."""
        # Mock the training facade to return success
        with patch('webhook_handler.run_training') as mock_run_training:
            mock_result = {
                "artifact_path": f"{temp_data_dir}/test_community/LATEST/policy.pt",
                "logs_path": f"{temp_data_dir}/test_community",
                "exp_name": "test_community"
            }
            mock_run_training.return_value = mock_result
            
            # Create the mock artifact file
            os.makedirs(os.path.dirname(mock_result["artifact_path"]), exist_ok=True)
            with open(mock_result["artifact_path"], "w") as f:
                f.write("mock_policy_data")

            # Mock the data directory path
            with patch('webhook_handler.os.makedirs'):
                with patch('webhook_handler.open', create=True) as mock_open:
                    with patch('webhook_handler.json.dump'):
                        with patch('webhook_handler.os.remove'):
                            response = client.post("/trigger-finetune", json=sample_dataset)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "policy_path" in data
            
            # Verify the training facade was called with correct parameters
            mock_run_training.assert_called_once_with(
                model_name="zephyr",
                datasets=["novalto"],
                loss_config={"name": "dpo", "beta": 0.1},
                exp_name="test_community"
            )

    @patch('webhook_handler.firebase_admin')
    def test_trigger_finetune_fallback_to_subprocess(self, mock_firebase, client, sample_dataset, temp_data_dir):
        """Test fallback to subprocess when training facade fails."""
        # Mock the training facade to fail
        with patch('webhook_handler.run_training') as mock_run_training:
            mock_run_training.side_effect = Exception("Facade failed")
            
            # Mock subprocess.run to succeed
            with patch('webhook_handler.subprocess.run') as mock_subprocess:
                # Create mock policy file
                policy_path = f".cache/root/test_community/LATEST/policy.pt"
                
                with patch('webhook_handler.os.path.exists') as mock_exists:
                    mock_exists.return_value = True
                    
                    with patch('webhook_handler.os.makedirs'):
                        with patch('webhook_handler.open', create=True):
                            with patch('webhook_handler.json.dump'):
                                with patch('webhook_handler.os.remove'):
                                    response = client.post("/trigger-finetune", json=sample_dataset)

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert data["policy_path"] == policy_path
                
                # Verify subprocess was called with correct command
                expected_command = [
                    "python", 
                    "train.py",
                    "model=zephyr",
                    "datasets=[novalto]",
                    "loss=dpo",
                    "loss.beta=0.1",
                    "exp_name=test_community"
                ]
                mock_subprocess.assert_called_once_with(expected_command, check=True)

    @patch('webhook_handler.firebase_admin')
    def test_trigger_finetune_missing_policy_file(self, mock_firebase, client, sample_dataset):
        """Test error handling when policy file is not created."""
        with patch('webhook_handler.run_training') as mock_run_training:
            mock_run_training.side_effect = Exception("Facade failed")
            
            with patch('webhook_handler.subprocess.run'):
                with patch('webhook_handler.os.path.exists') as mock_exists:
                    mock_exists.return_value = False  # Policy file doesn't exist
                    
                    with patch('webhook_handler.os.makedirs'):
                        with patch('webhook_handler.open', create=True):
                            with patch('webhook_handler.json.dump'):
                                with patch('webhook_handler.os.remove'):
                                    response = client.post("/trigger-finetune", json=sample_dataset)

                assert response.status_code == 500
                data = response.json()
                assert "Fine-tuning failed: policy.pt not found" in data["detail"]

    @patch('webhook_handler.firebase_admin')
    def test_trigger_finetune_invalid_payload(self, mock_firebase, client):
        """Test error handling for invalid request payload."""
        invalid_payload = {"invalid": "data"}
        
        response = client.post("/trigger-finetune", json=invalid_payload)
        
        assert response.status_code == 500
        data = response.json()
        assert "Error:" in data["detail"]

    @patch('webhook_handler.firebase_admin')
    def test_trigger_finetune_missing_dataset(self, mock_firebase, client):
        """Test error handling when dataset key is missing."""
        invalid_payload = {"communityId": "test", "wrong_key": []}
        
        response = client.post("/trigger-finetune", json=invalid_payload)
        
        assert response.status_code == 500
        data = response.json()
        assert "Error:" in data["detail"]

    @patch('webhook_handler.firebase_admin')
    def test_trigger_finetune_cleanup_on_error(self, mock_firebase, client, sample_dataset):
        """Test that dataset file is cleaned up even when errors occur."""
        with patch('webhook_handler.run_training') as mock_run_training:
            mock_run_training.side_effect = Exception("Training failed")
            
            with patch('webhook_handler.os.makedirs'):
                with patch('webhook_handler.open', create=True):
                    with patch('webhook_handler.json.dump'):
                        with patch('webhook_handler.os.path.exists') as mock_exists:
                            mock_exists.return_value = True  # File exists
                            
                            with patch('webhook_handler.os.remove') as mock_remove:
                                response = client.post("/trigger-finetune", json=sample_dataset)

                            # Verify cleanup was called
                            mock_remove.assert_called()

        assert response.status_code == 500

    def test_trigger_finetune_dataset_validation(self, client):
        """Test that the dataset format is properly validated."""
        # This is an integration test that would run with the actual validation
        # if the dataset validation tools are integrated into the API
        valid_dataset = {
            "communityId": "validation_test",
            "dataset": [
                {
                    "prompt": "Valid prompt",
                    "chosen": "Good response",
                    "rejected": "Bad response"
                }
            ]
        }
        
        # Mock everything to focus on the validation aspect
        with patch('webhook_handler.firebase_admin'):
            with patch('webhook_handler.run_training') as mock_training:
                mock_training.return_value = {
                    "artifact_path": "/mock/path/policy.pt",
                    "logs_path": "/mock/path",
                    "exp_name": "validation_test"
                }
                
                with patch('webhook_handler.os.makedirs'):
                    with patch('webhook_handler.open', create=True):
                        with patch('webhook_handler.json.dump') as mock_dump:
                            with patch('webhook_handler.os.remove'):
                                response = client.post("/trigger-finetune", json=valid_dataset)

                # Verify the dataset was saved with the correct format
                mock_dump.assert_called_once()
                saved_dataset = mock_dump.call_args[0][0]
                assert len(saved_dataset) == 1
                assert "prompt" in saved_dataset[0]
                assert "chosen" in saved_dataset[0]
                assert "rejected" in saved_dataset[0]

        assert response.status_code == 200


class TestAPIIntegrationWithPackages:
    """Integration tests that verify the API works with the reorganized package structure."""

    def test_training_package_import(self):
        """Test that the training package can be imported successfully."""
        from training import run_training
        assert callable(run_training)

    def test_datasets_package_import(self):
        """Test that the datasets package can be imported successfully."""
        from datasets import PreferenceDatasetInterface
        assert PreferenceDatasetInterface is not None

    def test_storage_package_import(self):
        """Test that the storage package can be imported successfully."""
        from storage import StorageInterface
        assert StorageInterface is not None

    def test_core_validators_import(self):
        """Test that the core validators can be imported successfully."""
        from core.validators import validate_training_config
        assert callable(validate_training_config)

    @patch('webhook_handler.firebase_admin')
    def test_end_to_end_mocked_pipeline(self, mock_firebase):
        """Test the complete pipeline with mocked components."""
        from webhook_handler import app
        client = TestClient(app)
        
        # Sample request
        request_data = {
            "communityId": "e2e_test",
            "dataset": [
                {
                    "prompt": "Test prompt",
                    "chosen": "Good response",
                    "rejected": "Bad response"
                }
            ]
        }
        
        # Mock the entire training process
        with patch('webhook_handler.run_training') as mock_training:
            mock_training.return_value = {
                "artifact_path": "/mock/e2e_test/LATEST/policy.pt",
                "logs_path": "/mock/e2e_test",
                "exp_name": "e2e_test"
            }
            
            with patch('webhook_handler.os.makedirs'):
                with patch('webhook_handler.open', create=True):
                    with patch('webhook_handler.json.dump'):
                        with patch('webhook_handler.os.remove'):
                            response = client.post("/trigger-finetune", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "policy_path" in data


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])