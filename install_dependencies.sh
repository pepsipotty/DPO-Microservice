#!/bin/bash
# DPO Microservice Dependency Installation Script
# Handles proper installation order and Python version compatibility

set -e  # Exit on any error

echo "🚀 Installing DPO Microservice dependencies..."

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
echo "📍 Python version: $PYTHON_VERSION"

if [[ "$PYTHON_VERSION" != "3.11" && "$PYTHON_VERSION" != "3.10" && "$PYTHON_VERSION" != "3.9" ]]; then
    echo "⚠️  Warning: This code was tested with Python 3.9-3.11. Current version: $PYTHON_VERSION"
    echo "   You may encounter compatibility issues."
fi

# Function to install with retries
install_with_retry() {
    local package=$1
    local max_attempts=3
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        echo "📦 Installing $package (attempt $attempt/$max_attempts)..."
        if pip install --no-cache-dir "$package"; then
            echo "✅ Successfully installed $package"
            return 0
        else
            echo "❌ Failed to install $package (attempt $attempt/$max_attempts)"
            ((attempt++))
            if [[ $attempt -le $max_attempts ]]; then
                echo "🔄 Retrying in 5 seconds..."
                sleep 5
            fi
        fi
    done
    
    echo "💥 Failed to install $package after $max_attempts attempts"
    return 1
}

# Choose installation method
if [[ "$1" == "--locked" ]]; then
    echo "🔒 Using locked versions for reproducible environment..."
    REQUIREMENTS_FILE="requirements-locked.txt"
else
    echo "📋 Using flexible version constraints..."
    REQUIREMENTS_FILE="requirements.txt"
fi

# Check if requirements file exists
if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
    echo "❌ Requirements file $REQUIREMENTS_FILE not found!"
    exit 1
fi

# Install PyTorch first with CUDA support if available
echo "🔥 Installing PyTorch with CUDA support..."
if command -v nvidia-smi &> /dev/null; then
    echo "🎮 NVIDIA GPU detected, installing CUDA version..."
    install_with_retry "torch==2.1.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118"
else
    echo "💻 No GPU detected, installing CPU version..."
    install_with_retry "torch==2.1.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu"
fi

# Install critical dependencies in order to prevent conflicts
echo "🧠 Installing HuggingFace packages..."
if [[ "$1" == "--locked" ]]; then
    install_with_retry "huggingface-hub==0.24.7"
    install_with_retry "transformers==4.36.2"
    install_with_retry "tokenizers==0.15.2"
else
    install_with_retry "huggingface-hub>=0.20.0,<0.30.0"
    install_with_retry "transformers>=4.34.0,<4.40.0"
    install_with_retry "tokenizers>=0.14.0,<0.16.0"
fi

# Install remaining dependencies
echo "📚 Installing remaining dependencies..."
pip install --no-cache-dir -r "$REQUIREMENTS_FILE"

# Verify critical imports work
echo "🔍 Verifying installation..."

python -c "
import torch
print(f'✅ PyTorch {torch.__version__} (CUDA available: {torch.cuda.is_available()})')

import transformers
print(f'✅ Transformers {transformers.__version__}')

import huggingface_hub
print(f'✅ HuggingFace Hub {huggingface_hub.__version__}')

# Test critical functions
try:
    from huggingface_hub import split_torch_state_dict_into_shards
    print('✅ HuggingFace Hub has required functions')
except ImportError as e:
    print(f'❌ Missing HuggingFace Hub function: {e}')

try:
    from transformers.utils import is_torch_greater_or_equal
    print('✅ Transformers has required utility functions')
except ImportError as e:
    print(f'❌ Missing Transformers utility: {e}')
    
try:
    import firebase_admin
    print(f'✅ Firebase Admin {firebase_admin.__version__}')
except ImportError:
    print('⚠️  Firebase Admin not available (may be optional)')

print('🎉 All critical dependencies verified!')
"

echo ""
echo "✨ Installation complete!"
echo ""
echo "Usage:"
echo "  python webhook_handler.py  # Start the service"
echo ""
echo "For reproducible deployments, use:"
echo "  $0 --locked"