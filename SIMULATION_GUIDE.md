# DPO API Simulation Guide

This guide shows how to use the `simulate_api.py` tool to troubleshoot fine-tuning issues without needing a running server or network connection.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create a Sample Dataset
```bash
python3 simulate_api.py create-sample --output my_dataset.json --num-samples 5
```

### 3. Test Direct Training
```bash
# Basic test with minimal examples for fast iteration
python3 simulate_api.py direct --dataset my_dataset.json --exp-name test-run --n-examples 10

# More verbose output for debugging
python3 simulate_api.py -v direct --dataset my_dataset.json --exp-name debug-run --n-examples 10
```

### 4. Test Full Pipeline
```bash
# Simulate the complete job queue processing
python3 simulate_api.py pipeline --dataset my_dataset.json --exp-name pipeline-test --n-examples 10
```

## Simulation Modes

### Direct Mode
- **Purpose**: Test core training logic directly
- **Bypasses**: Web layer, authentication, job queue, database
- **Best for**: Debugging training code, dataset format issues, model configuration problems
- **Speed**: Fastest iteration

```bash
python3 simulate_api.py direct --dataset data.json --exp-name my-exp [options]
```

### Pipeline Mode  
- **Purpose**: Test the full microservice pipeline
- **Bypasses**: Only web layer and authentication 
- **Includes**: Job queue processing, database operations, run tracking
- **Best for**: Debugging integration issues, job queue problems, run management

```bash
python3 simulate_api.py pipeline --dataset data.json --exp-name my-exp [options]
```

## Common Options

| Option | Description | Default |
|--------|-------------|---------|
| `--dataset` | Path to JSON dataset file | Required |
| `--exp-name` | Experiment name | Required |
| `--model` | Base model (zephyr, gpt2, etc.) | zephyr |
| `--algo` | Training algorithm (dpo, ipo) | dpo |
| `--batch-size` | Training batch size | 8 |
| `--n-examples` | Number of training examples | 80 |
| `-v, --verbose` | Enable verbose logging | False |

## Dataset Format

Your dataset should be a JSON array of DPO records:

```json
[
  {
    "prompt": "What is the best approach to learn programming?",
    "responses": [
      "Start with Python as it's beginner-friendly...",
      "Just dive into any language immediately..."
    ],
    "pairs": [[0, 1]],  // [preferred_index, rejected_index]
    "sft_target": "Start with Python as it's beginner-friendly..."
  }
]
```

## Troubleshooting Common Issues

### Missing Dependencies
```bash
❌ Error: No module named 'hydra'
✅ Solution: pip install -r requirements.txt
```

### Dataset Format Errors
```bash
❌ Error: Record 0 missing required field: 'pairs'
✅ Solution: Use create-sample to see correct format
```

### GPU/Memory Issues
```bash
❌ Error: CUDA out of memory
✅ Solution: Reduce --batch-size and --n-examples
```

### Model Configuration Issues
```bash
❌ Error: Model 'custom-model' not found
✅ Solution: Use supported models (zephyr, gpt2, pythia-2.8b, pythia-6.9b)
```

## Integration Testing Workflow

1. **Start with sample data**: `create-sample` → verify basic functionality
2. **Test with your data**: Use direct mode with small dataset first
3. **Increase complexity**: Gradually increase dataset size and training examples  
4. **Full pipeline test**: Use pipeline mode to test integration
5. **Production ready**: Deploy to actual API endpoints

## Performance Tips

- **Fast iteration**: Use `--n-examples 10` for quick testing
- **Memory efficiency**: Use `--batch-size 2` for large models
- **Debug mode**: Always enabled in simulation (disables wandb, reduces overhead)
- **Cleanup**: Temporary files are automatically cleaned up

## Example Workflows

### Debug Training Failures
```bash
# 1. Create minimal test case
python3 simulate_api.py create-sample --output debug.json --num-samples 2

# 2. Test direct training with verbose logging
python3 simulate_api.py -v direct --dataset debug.json --exp-name debug --n-examples 5

# 3. If successful, test with real dataset
python3 simulate_api.py direct --dataset my_real_data.json --exp-name real-test --n-examples 20
```

### Validate Dataset Format
```bash
# The tool automatically validates your dataset format
python3 simulate_api.py direct --dataset questionable_data.json --exp-name validate-only --n-examples 1
```

### Compare Models/Algorithms
```bash
# Test different configurations quickly
python3 simulate_api.py direct --dataset data.json --exp-name dpo-test --algo dpo --n-examples 10
python3 simulate_api.py direct --dataset data.json --exp-name ipo-test --algo ipo --n-examples 10
```

## Advanced Usage

### Custom Training Parameters
You can modify the simulation code to test different training configurations:
- Edit `simulate_direct_training()` or `simulate_pipeline_mode()` functions
- Add new command-line arguments for additional parameters
- Test edge cases by modifying the mock data

### Integration with CI/CD
The simulation tool returns proper exit codes and can be used in automated testing:
```bash
# In your CI pipeline
python3 simulate_api.py direct --dataset test_data.json --exp-name ci-test --n-examples 5
if [ $? -eq 0 ]; then
    echo "✅ Training simulation passed"
else
    echo "❌ Training simulation failed"
    exit 1
fi
```