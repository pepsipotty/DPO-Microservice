FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/requirements.txt

# Install system dependencies and Python packages
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir "huggingface_hub==0.23.0" && \
    pip install --no-cache-dir -r requirements.txt

# Copy package structure (organized codebase)
COPY core/ /app/core/
COPY datasets/ /app/datasets/
COPY storage/ /app/storage/
COPY training/ /app/training/
COPY tools/ /app/tools/
COPY tests/ /app/tests/

# Copy configuration files
COPY config/ /app/config/

# Copy main application files
COPY webhook_handler.py /app/webhook_handler.py
COPY train.py /app/train.py
COPY trainers.py /app/trainers.py
COPY utils.py /app/utils.py

# Copy legacy files (for backward compatibility)
COPY preference_datasets.py /app/preference_datasets.py
COPY upload_to_bucket.py /app/upload_to_bucket.py
COPY upload_test.py /app/upload_test.py
COPY testing_datasets.py /app/testing_datasets.py

# Create data directory (runtime volume mount point)
RUN mkdir -p /app/data

# Set environment variables
ENV WANDB_DISABLED=true
ENV PYTHONPATH=/app

# Gateway integration environment variables (set defaults for development)
ENV DPO_GATEWAY_SHARED_SECRET=""
ENV DPO_SERVICE_TTL_SECONDS=21600
ENV DPO_MAX_CONCURRENT_JOBS=2
ENV DPO_JOB_TIMEOUT_SECONDS=3600
ENV DPO_MAX_DATASET_SIZE_MB=5
ENV DPO_RATE_LIMIT_PER_MINUTE=5
ENV DPO_WORKING_DIR=/app
ENV DPO_CACHE_DIR=/app/.cache

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the webhook server
CMD ["uvicorn", "webhook_handler:app", "--host", "0.0.0.0", "--port", "8000"]