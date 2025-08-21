# DPO Microservice Integration Context

## Overview

This document provides essential information for integrating with the DPO (Direct Preference Optimization) microservice. The service is production-ready and provides a FastAPI webhook endpoint for fine-tuning language models using preference data.

## API Endpoints

### POST `/trigger-finetune`

Triggers a DPO training job with preference data.

**Request Format:**
```json
{
  "communityId": "unique_community_identifier",
  "dataset": [
    {
      "chosen": "This is the preferred response",
      "rejected": "This is the less preferred response", 
      "prompt": "What is the question or context?"
    }
  ]
}
```

**Response Format:**
```json
{
  "status": "success",
  "policy_path": "/path/to/trained/model/policy.pt"
}
```

**Error Responses:**
```json
{
  "detail": "Error: [specific error message]"
}
```

### GET `/health`

Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "service": "dpo-microservice"
}
```

## Dataset Format

The service expects preference data in "novalto" format with these required fields:

- `chosen`: The preferred response text
- `rejected`: The less preferred response text  
- `prompt`: The input prompt or context

**Validation**: Dataset is automatically validated for format and content quality.

## Environment Configuration

### Required Environment Variables

```bash
# Firebase Configuration (for model storage)
FIREBASE_CREDENTIALS_PATH=/path/to/serviceKey.json
STORAGE_BUCKET=your-firebase-storage-bucket

# Optional Configuration
WANDB_DISABLED=true  # Disable weights & biases logging
PYTHONPATH=/app      # For container deployment
```

### Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Generate toy dataset for testing
make toy-data

# Start the API server
make api
# OR: uvicorn webhook_handler:app --host 0.0.0.0 --port 8000

# Test the full pipeline
make toy-trigger
```

### Docker Deployment

```bash
# Build container
make docker-build
# OR: docker build -t dpo-microservice .

# Run container
docker run -p 8000:8000 -v $(PWD)/data:/app/data dpo-microservice
```

## Integration Testing

### Test Endpoint Connectivity

```bash
# Health check
curl http://localhost:8000/health

# Test training trigger
curl -X POST "http://localhost:8000/trigger-finetune" \
  -H "Content-Type: application/json" \
  -d '{
    "communityId": "test_123",
    "dataset": [
      {
        "chosen": "Great response",
        "rejected": "Poor response", 
        "prompt": "Test prompt"
      }
    ]
  }'
```

### Generate Test Data

```bash
# Create toy dataset
python tools/make_toy_novalto.py --out data/test_dataset.json --size 10

# Validate dataset format
python tools/validate_novalto.py data/test_dataset.json --stats
```

## Model Configuration

### Supported Models
- `zephyr` (default for API endpoint)
- `gpt2-large`, `gpt2-xl`
- `pythia28`, `pythia69`
- `llama7b`, `gptj`

### Training Parameters
- **Loss Function**: DPO (Direct Preference Optimization) with beta=0.1
- **Batch Size**: 128 (configurable based on GPU memory)
- **Trainer**: FSDPTrainer (Fully Sharded Data Parallel) for multi-GPU
- **Max Length**: 512 tokens
- **Max Prompt Length**: 256 tokens

## Storage and Artifacts

### Firebase Storage Structure
```
policies/
  {communityId}/
    LATEST/
      policy.pt          # Trained model weights
      config.yaml        # Training configuration
      metrics.json       # Training metrics
```

### Local Development Storage
```
.cache/
  {communityId}/
    LATEST/
      policy.pt          # Same structure as Firebase
```

## Error Handling

### Common Issues
1. **Dataset validation errors**: Check that all required fields are present
2. **Training failures**: Verify GPU memory and model configuration
3. **Storage errors**: Ensure Firebase credentials are properly configured
4. **Memory issues**: Reduce batch size for smaller GPU configurations

### Logs and Debugging
- Training logs: Written to experiment directory
- API logs: Available through container logs
- Health endpoint: Returns service status

## Security Considerations

### Credentials
- Firebase service key should be mounted as a volume in production
- Use environment variables for sensitive configuration
- Avoid committing credentials to version control

### Data Privacy
- Training datasets are temporarily stored during processing
- Datasets are automatically cleaned up after training completion
- Model artifacts are stored in configured storage backend

## Performance Notes

### Resource Requirements
- **Minimum**: 8GB GPU memory for small models
- **Recommended**: 16GB+ GPU memory for stable training
- **CPU**: 4+ cores recommended
- **Storage**: 10GB+ free space for model artifacts

### Training Time
- Small datasets (100 examples): ~5-10 minutes
- Medium datasets (1000 examples): ~30-60 minutes
- Large datasets (10000+ examples): 2+ hours

## Support and Troubleshooting

### Development Commands
```bash
make setup          # Complete environment setup
make test           # Run test suite
make toy-trigger    # End-to-end pipeline test
make validate-structure  # Verify package imports
```

### Container Health Check
The service includes built-in health monitoring accessible at `/health` endpoint for load balancer integration.

---

**Version**: 1.0 Production Ready  
**Last Updated**: August 2025  
**Contact**: See project repository for issues and support