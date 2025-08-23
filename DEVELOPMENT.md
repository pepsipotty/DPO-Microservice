# Development Guide

This file provides development guidance and architecture overview for the DPO microservice.

## Project Overview

This is a DPO (Direct Preference Optimization) microservice that provides a FastAPI webhook endpoint for fine-tuning language models using preference data. The project is built on the reference DPO implementation and includes a custom dataset handler for the "novalto" dataset format.

## Architecture

The project consists of two main operational modes:

1. **Training Mode**: Direct command-line training using `train.py` with Hydra configuration
2. **Microservice Mode**: FastAPI webhook service (`webhook_handler.py`) that accepts training requests via HTTP POST

### Core Components

- `train.py`: Main training entry point using Hydra configuration framework
- `trainers.py`: Multiple trainer implementations (BasicTrainer, FSDPTrainer, TensorParallelTrainer)
- `preference_datasets.py`: Dataset loading and processing, includes custom `novalto` dataset handler
- `webhook_handler.py`: FastAPI service that triggers training jobs
- `upload_to_bucket.py`: Firebase Storage integration for model artifact uploads
- `utils.py`: Shared utilities and helper functions

### Configuration System

Uses Hydra configuration with YAML files in `config/`:
- `config/config.yaml`: Main training configuration
- `config/model/*.yaml`: Model-specific configurations (zephyr, pythia, llama, etc.)
- `config/loss/*.yaml`: Loss function configurations (dpo, sft)

## Common Commands

### Training Commands

**SFT (Supervised Fine-Tuning):**
```bash
python train.py model=pythia28 datasets=[hh] loss=sft exp_name=my_sft_run gradient_accumulation_steps=2 batch_size=64 eval_batch_size=32 trainer=FSDPTrainer sample_during_eval=false
```

**DPO Training:**
```bash
python train.py model=pythia28 datasets=[hh] loss=dpo loss.beta=0.1 model.archive=/path/to/sft/checkpoint/policy.pt exp_name=my_dpo_run gradient_accumulation_steps=2 batch_size=32 eval_batch_size=32 trainer=FSDPTrainer sample_during_eval=false
```

**Zephyr with Custom Dataset (used by webhook):**
```bash
python train.py model=zephyr datasets=[novalto] loss=dpo loss.beta=0.1 exp_name=community_123
```

### Development Commands

**Install Dependencies:**
```bash
pip install -r requirements.txt
```

**Run Webhook Service:**
```bash
uvicorn webhook_handler:app --host 0.0.0.0 --port 8000
```

**Docker Build:**
```bash
docker build -t dpo-microservice .
```

**Test Webhook Endpoint:**
```bash
curl -X POST "http://localhost:8000/trigger-finetune" \
  -H "Content-Type: application/json" \
  -d '{"communityId": "test_123", "dataset": [...]}'
```

## Key Implementation Details

### Webhook Service Flow
1. Receives POST request with `communityId` and `dataset` fields
2. Saves dataset to `/app/data/dataset.json`
3. Runs DPO training with hardcoded zephyr model and novalto dataset handler
4. Verifies `policy.pt` generation in `.cache/root/{communityId}/LATEST/policy.pt`
5. Cleans up dataset file after completion

### Custom Dataset Handler
The `novalto` dataset handler in `preference_datasets.py:get_novalto_dataset()` reads from `/app/data/dataset.json` and expects a specific format for preference pairs.

### Model Configurations
- Default trainer: `FSDPTrainer` (Fully Sharded Data Parallel)
- Default optimizer: `RMSprop`
- Evaluation frequency: Every 20,000 examples
- Default batch size: 128 (configurable per GPU setup)

### Firebase Integration
- Uses `serviceKey.json` for Firebase Admin SDK authentication
- Uploads trained models to `dpo-frontend.firebasestorage.app` bucket
- Upload function: `trigger_policy_upload()` in `upload_to_bucket.py`

## Environment Setup

The microservice runs in a containerized environment with:
- Python 3.9
- WANDB disabled (`WANDB_DISABLED=true`)
- Working directory: `/app`
- Exposed port: 8000

## Trainer Selection

- **BasicTrainer**: Single GPU or simple multi-GPU setup
- **FSDPTrainer**: Recommended for multi-GPU training with model sharding
- **TensorParallelTrainer**: Experimental tensor parallelism (may have slow sampling)

For FSDP training, you may need to run `ulimit -n 64000` before training.