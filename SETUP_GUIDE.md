# DPO Microservice Setup Guide

## Quick Setup for New Runpod Instances

### 1. Clone Repository
```bash
cd /workspace
git clone https://github.com/pepsipotty/DPO-Microservice.git
cd DPO-Microservice
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. **CRITICAL: Add Firebase Credentials**
The repository does NOT include `serviceKey.json` for security reasons. You must add it manually:

1. Copy your Firebase service account JSON file to the project root
2. Rename it to `serviceKey.json`
3. Ensure it's in the same directory as `upload_to_bucket.py`

**Example:**
```bash
# Copy from local machine to Runpod
scp path/to/your/serviceKey.json runpod:/workspace/DPO-Microservice/
```

**Or create it directly on Runpod:**
```bash
nano serviceKey.json
# Paste the JSON content and save
```

### 4. Verify Setup
```bash
# Test Firebase connectivity
python -c "from upload_to_bucket import trigger_policy_upload; print('✅ Firebase setup successful')"
```

### 5. Run Training
```bash
# Test with simulation tool
python simulate_api.py direct --dataset data/test_dataset.json --exp-name test-setup --model gpt2-large --n-examples 32
```

## What's Included
- ✅ All training pipeline fixes (n_examples type error, FSDP compatibility, etc.)
- ✅ Automatic cleanup functionality (saves 6GB+ per training run)
- ✅ Firebase upload integration
- ✅ Comprehensive simulation and testing tools
- ✅ Full troubleshooting documentation

## What's NOT Included
- ❌ Firebase service account credentials (`serviceKey.json`)
- ❌ Training model cache (will be downloaded on first use)

## Firebase Storage Details
- **Bucket**: `dpo-frontend.firebasestorage.app`
- **Storage Path**: `policies/{filename}`
- **Upload**: Automatic after successful training
- **Cleanup**: Automatic removal of local files after successful upload

## Troubleshooting
- If Firebase upload fails with "Invalid JWT Signature", check that `serviceKey.json` is valid and properly formatted
- If training fails, see `troubleshooting_report.md` for complete debugging guide
- All training logs are preserved in `.cache/root/` directories