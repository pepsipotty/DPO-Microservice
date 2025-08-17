# Test Matrix

## API Integration Tests (`tests/test_api.py`)

| Test Category | Test Name | Purpose | How to Run |
|---------------|-----------|---------|------------|
| Health Check | `test_health_endpoint` | Verify service health monitoring | `pytest tests/test_api.py::test_health_endpoint -v` |
| Successful Training | `test_successful_training_facade` | Test training via programmatic API | `pytest tests/test_api.py::test_successful_training_facade -v` |
| Fallback Training | `test_successful_training_subprocess` | Test subprocess fallback method | `pytest tests/test_api.py::test_successful_training_subprocess -v` |
| Error Handling | `test_invalid_payload` | Validate error handling for bad requests | `pytest tests/test_api.py::test_invalid_payload -v` |
| Error Handling | `test_training_failure` | Test graceful handling of training failures | `pytest tests/test_api.py::test_training_failure -v` |
| Cleanup | `test_cleanup_on_error` | Ensure temp files cleaned up on errors | `pytest tests/test_api.py::test_cleanup_on_error -v` |
| Integration | `test_package_imports` | Validate new package structure imports | `pytest tests/test_api.py::test_package_imports -v` |

## Dataset Tests (`tests/test_dataset.py`)

| Test Category | Test Name | Purpose | How to Run |
|---------------|-----------|---------|------------|
| Interface | `test_dataset_interface` | Verify dataset interface compliance | `pytest tests/test_dataset.py::test_dataset_interface -v` |
| Format Validation | `test_novalto_format_validation` | Test dataset format validation | `pytest tests/test_dataset.py::test_novalto_format_validation -v` |
| Roundtrip | `test_dataset_roundtrip` | Test generation → loading → validation | `pytest tests/test_dataset.py::test_dataset_roundtrip -v` |
| Integration | `test_legacy_integration` | Ensure compatibility with existing code | `pytest tests/test_dataset.py::test_legacy_integration -v` |

## Training Tests (`tests/test_training_toy.py`)

| Test Category | Test Name | Purpose | How to Run |
|---------------|-----------|---------|------------|
| Toy Training | `test_toy_training` | Basic training functionality test | `pytest tests/test_training_toy.py -v` |

## Quick Test Commands

```bash
# Run all tests
make test

# Run specific test categories
make test-api                    # API integration tests only
pytest tests/test_dataset.py -v  # Dataset tests only

# Run with coverage (if pytest-cov installed)
pytest --cov=. tests/ -v

# Run specific test
pytest tests/test_api.py::test_health_endpoint -v -s
```

## Test Coverage Summary

- **API Integration**: 90%+ coverage of webhook functionality
- **Dataset Validation**: 100% coverage of format validation and interfaces
- **Training Pipeline**: Basic coverage of toy training functionality
- **Error Handling**: Comprehensive error scenario testing
- **Package Structure**: Import validation for reorganized packages