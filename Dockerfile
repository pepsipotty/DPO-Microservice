FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir "huggingface_hub==0.23.0" && \
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

# Copy service key if it exists (can be overridden by environment variables)
COPY serviceKey.json* /app/

# Set environment variables
ENV WANDB_DISABLED=true
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the webhook server
CMD ["uvicorn", "webhook_handler:app", "--host", "0.0.0.0", "--port", "8000"]