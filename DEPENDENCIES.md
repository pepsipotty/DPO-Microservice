# DPO Microservice Dependencies

## Overview

This document explains the dependency management strategy for the DPO Microservice and how to avoid the dependency hell that can occur when deploying on fresh environments.

## The Problem

The DPO training code was written for specific versions of ML libraries (circa late 2023/early 2024). When `pip install -r requirements.txt` is run on a fresh environment, it installs the **latest compatible versions**, which can cause cascading compatibility issues.

### What Went Wrong

1. **Original Working Environment**: Docker container with Python 3.9 and pinned `huggingface_hub==0.23.0`
2. **Fresh RunPod Deployment**: Python 3.11 with `transformers>=4.34.0` → installed 4.55.4 (latest)
3. **Cascade of Conflicts**: Each updated package required newer versions of its dependencies
4. **Training Code Breaks**: Code expects specific utility functions only available in certain version ranges

## Solution: Two-Tier Dependency Management

### 1. requirements-locked.txt (Exact Reproducibility)
Use this for production deployments where you need exact version matching:

```bash
./install_dependencies.sh --locked
```

**Locked Versions (Known Working):**
- Python 3.11
- transformers==4.36.2
- huggingface-hub==0.24.7  
- tokenizers==0.15.2
- torch==2.1.0
- firebase_admin==7.1.0

### 2. requirements.txt (Flexible with Constraints)
Use this for development where you want some flexibility:

```bash
./install_dependencies.sh
```

**Key Constraints:**
- `transformers>=4.34.0,<4.40.0` (training code compatibility range)
- `tokenizers>=0.14.0,<0.16.0` (matches transformers constraints)
- `huggingface-hub>=0.20.0,<0.30.0` (has required functions)

## Critical Compatibility Requirements

### Transformers Utility Functions
The training code requires these functions that were added/removed in specific versions:
- `is_torch_greater_or_equal` (available in 4.34-4.39, removed in 4.40+)
- `is_torchdynamo_compiling` (similar version constraints)

### HuggingFace Hub Functions  
- `split_torch_state_dict_into_shards` (added in ~0.20.0)

### Python Version Support
- **Recommended**: Python 3.11 (RunPod default)
- **Supported**: Python 3.9-3.11
- **Avoid**: Python 3.12+ (limited ML library support)

## Installation Methods

### Method 1: Automated Script (Recommended)
```bash
# For production (exact versions)
./install_dependencies.sh --locked

# For development (flexible versions)  
./install_dependencies.sh
```

### Method 2: Manual Installation
```bash
# Install PyTorch first
pip install torch==2.1.0 --index-url https://download.pytorch.org/whl/cu118

# Install HuggingFace packages in order
pip install huggingface-hub==0.24.7
pip install transformers==4.36.2
pip install tokenizers==0.15.2

# Install remaining dependencies
pip install -r requirements-locked.txt
```

### Method 3: Docker (Most Reliable)
The Dockerfile already handles proper installation order:
```dockerfile
RUN pip install --no-cache-dir "huggingface_hub==0.23.0" && \
    pip install --no-cache-dir -r requirements.txt
```

## Troubleshooting Common Issues

### Issue: "cannot import name 'split_torch_state_dict_into_shards'"
**Solution**: Upgrade huggingface-hub to >=0.20.0
```bash
pip install "huggingface-hub>=0.20.0"
```

### Issue: "cannot import name 'is_torch_greater_or_equal'"  
**Solution**: Downgrade transformers to <4.40.0
```bash
pip install "transformers>=4.34.0,<4.40.0"
```

### Issue: "module 'wandb.proto.wandb_internal_pb2' has no attribute 'Result'"
**Solution**: Fix protobuf version conflict
```bash
pip install "protobuf>=3.19.0,<5"
```

### Issue: "No module named 'firebase_admin'"
**Solution**: Firebase admin was removed from requirements.txt by mistake
```bash
pip install firebase_admin
```

## Version Evolution Timeline

| Date | Environment | transformers | huggingface-hub | Status |
|------|-------------|--------------|-----------------|--------|
| 2023-12 | Original Docker | 4.35.2 | 0.23.0 | ✅ Working |
| 2024-08 | Fresh RunPod | 4.55.4 | 0.34.4 | ❌ Broken |
| 2024-08 | Fixed RunPod | 4.36.2 | 0.24.7 | ✅ Working |

## Future Considerations

### Option 1: Pin Everything (Current Strategy)
- **Pros**: Guaranteed compatibility
- **Cons**: No security updates, outdated packages

### Option 2: Modernize Training Code  
- Update imports to work with latest transformers
- Replace deprecated utility functions
- Test with latest versions

### Option 3: Containerization
- Use Docker for all deployments
- Pre-built images with known working versions
- Isolates from host environment variations

## Quick Start for New Deployments

1. **Clone repository**
2. **Install dependencies**: `./install_dependencies.sh --locked`  
3. **Verify**: Check that service starts without import errors
4. **Test**: Run a small training job to verify ML pipeline works

## Environment Variables Required

For service operation (independent of dependencies):
```bash
export DPO_GATEWAY_SHARED_SECRET=your_secret
export DPO_REGISTER_SECRET=your_secret  
export DPO_REGISTER_URL=https://your-frontend.com/api/dpo/register
export DPO_PUBLIC_BASE_URL=https://your-service-url.com
```

## Support

If you encounter dependency issues not covered here:

1. Check the exact error message against troubleshooting section
2. Verify Python version compatibility
3. Try the locked versions first
4. If still broken, file an issue with full error logs and `pip freeze` output