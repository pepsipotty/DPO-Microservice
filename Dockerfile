FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy necessary files
COPY train.py trainers.py preference_datasets.py upload_to_bucket.py webhook_handler.py utils.py requirements.txt /app/
COPY config /app/config
COPY data /app/data
COPY serviceKey.json /app/serviceKey.json

RUN pip install --no-cache-dir "huggingface_hub==0.23.0"
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
# Start the webhook
CMD ["uvicorn", "webhook_handler:app", "--host", "0.0.0.0", "--port", "8000"]
ENV WANDB_DISABLED=true