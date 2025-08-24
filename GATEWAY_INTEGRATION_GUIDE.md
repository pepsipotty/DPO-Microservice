# DPO Microservice - Gateway Integration Technical Reference

## 1. API Surface

### 1.1 Health Check
**Endpoint:** `GET /health`  
**Authentication:** None required  
**Response (200 OK):**
```json
{
  "ok": true,
  "version": "1.0.0",
  "uptime_s": 3600,
  "queue_stats": {
    "total_runs": 42,
    "queued": 2,
    "running": 1,
    "completed": 35,
    "failed": 3,
    "cancelled": 1,
    "queue_size": 2,
    "active_jobs": 1
  }
}
```

### 1.2 Trigger Fine-tuning
**Endpoint:** `POST /trigger-finetune`  
**Authentication:** HMAC + Admin required  
**Request Body:**
```json
{
  "kb_id": "knowledge_base_123",
  "base_model": "zephyr",        // Optional, default: "zephyr"
  "algo": "dpo",                  // Optional, default: "dpo"
  "exp_name": "experiment_v1",
  "dataset_inline": [             // Option 1: Inline dataset
    {
      "prompt": "What is AI?",
      "chosen": "AI is artificial intelligence...",
      "rejected": "AI means nothing..."
    }
  ]
  // OR
  "dataset_url": "https://storage.example.com/dataset.jsonl"  // Option 2: URL
}
```

**Response (200 OK):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

**Error Responses:**
- `401`: Invalid/missing HMAC signature or malformed user claims
- `403`: Valid HMAC but admin=false (admin privileges required)
- `429`: Rate limit exceeded or active job exists for kb_id
- `400`: Invalid dataset format or missing required fields
- `413`: Dataset too large (>5MB)

### 1.3 Get Run Status
**Endpoint:** `GET /runs/{run_id}`  
**Authentication:** HMAC required  
**Response (200 OK):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",  // One of: queued|running|completed|failed|cancelled
  "metrics": {          // Optional, when completed
    "loss": 0.234,
    "accuracy": 0.89
  },
  "started_at": 1703001234,   // Unix timestamp (optional)
  "finished_at": 1703005678    // Unix timestamp (optional)
}
```

### 1.4 Get Run Artifacts
**Endpoint:** `GET /runs/{run_id}/artifacts`  
**Authentication:** HMAC required  
**Response (200 OK):**
```json
{
  "checkpoint_url": "https://storage.example.com/checkpoints/model.pt",
  "report_url": "https://storage.example.com/reports/metrics.json",
  "logs_url": "https://storage.example.com/logs/training.log"
}
```

### 1.5 Cancel Run
**Endpoint:** `DELETE /runs/{run_id}`  
**Authentication:** HMAC required  
**Response (200 OK):**
```json
{
  "status": "cancelled"
}
```

## 2. Auth & Security

### 2.1 HMAC Verification

**Required Headers:**
- `X-Novalto-User`: Base64-encoded JSON containing user claims
- `X-Novalto-Signature`: Hex-encoded HMAC-SHA256 signature

**Canonical String Format:**
```
METHOD\n
PATH\n
<SHA256_HEX_OF_REQUEST_BODY>\n
<BASE64_X_NOVALTO_USER_VALUE>
```

**Example Canonical String:**
```
POST
/trigger-finetune
a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3
eyJ1aWQiOiJ1c2VyMTIzIiwiZW1haWwiOiJ1c2VyQGV4YW1wbGUuY29tIiwiYWRtaW4iOnRydWV9
```

**Signature Computation (Python):**
```python
import hmac
import hashlib

def compute_signature(canonical_string: str, shared_secret: str) -> str:
    return hmac.new(
        shared_secret.encode('utf-8'),
        canonical_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
```

### 2.2 User Claims Structure

**X-Novalto-User Header Value (before Base64):**
```json
{
  "uid": "user_123",
  "email": "user@example.com",
  "admin": true    // Must be true for /trigger-finetune
}
```

**Admin Enforcement:**
- `POST /trigger-finetune`: Requires `admin: true`
- `GET /runs/{id}`: Non-admins can only access their own runs (matched by uid)
- `GET /runs/{id}/artifacts`: Same as above
- `DELETE /runs/{id}`: Same as above

## 3. Registration Flow

### 3.1 Registration Request

**Endpoint:** Value of `DPO_REGISTER_URL` environment variable  
**Method:** `POST`  
**Required Header:**
```
X-DPO-Register-Secret: <value_from_DPO_REGISTER_SECRET>
```

**Request Body:**
```json
{
  "base_url": "https://dpo-service.internal.example.com",
  "version": "1.0.0",
  "ttl_seconds": 21600  // 6 hours default
}
```

### 3.2 TTL Handling

- Service registers immediately on startup
- Re-registers at 75% of TTL (e.g., every 4.5 hours if TTL=6 hours)
- On failure, retries with exponential backoff (30s → 60s → 120s → max 300s)
- Unregisters on graceful shutdown (`DELETE` to same endpoint)

### 3.3 Registration Responses

- `200/201/204`: Registration successful
- `4xx`: Registration failed (check credentials/payload)
- `5xx`: Gateway error (will retry)

## 4. Trigger Payload Details

### 4.1 Dataset Options

**Option 1: Inline Dataset**
```json
{
  "dataset_inline": [
    {
      "prompt": "Question or context",
      "chosen": "Preferred response",
      "rejected": "Less preferred response"
    }
  ]
}
```
- Maximum size: 5MB (configurable via `DPO_MAX_DATASET_SIZE_MB`)
- All fields required and must be non-empty strings

**Option 2: URL Dataset**
```json
{
  "dataset_url": "https://storage.example.com/dataset.jsonl"
}
```
- Supported formats:
  - `.json`: JSON array of records
  - `.jsonl`: Newline-delimited JSON
  - `.jsonl.gz`: Gzipped JSONL
- Must use HTTPS or HTTP protocol
- Maximum download size: 5MB
- Timeout: 60 seconds

### 4.2 Validation Rules

- Must provide exactly one of `dataset_inline` or `dataset_url`
- Each record must have `prompt`, `chosen`, `rejected` fields
- All string fields must have `min_length: 1`
- `kb_id` and `exp_name` are required
- `base_model` defaults to "zephyr"
- `algo` defaults to "dpo"

### 4.3 Rate Limiting

- Per-user limit: 5 requests per minute
- Per kb_id limit: 1 concurrent training job
- Returns `429 Too Many Requests` when exceeded

## 5. Run Lifecycle

### 5.1 Status Transitions

```
queued → running → completed
                 ↘ failed
                 ↘ cancelled

queued → cancelled (if cancelled before processing)
running → cancelled (if cancelled during processing)
```

### 5.2 Status Vocabulary

**IMPORTANT:** The service NEVER returns "succeeded" - only these exact statuses:
- `queued`: Job waiting in queue
- `running`: Job actively processing
- `completed`: Job finished successfully
- `failed`: Job failed with error
- `cancelled`: Job cancelled by user or system

### 5.3 Artifacts

Artifacts are stored externally (e.g., Firebase) and URLs are returned via `/runs/{id}/artifacts`:
- `checkpoint_url`: Trained model checkpoint (.pt file)
- `report_url`: Training metrics report (JSON)
- `logs_url`: Training logs (text file)

Note: URLs are not signed by this service; they point to external storage.

## 6. Deployment & Operations

### 6.1 Service Launch

**Default Port:** 8000  
**Launch Command (in container):**
```bash
uvicorn webhook_handler:app --host 0.0.0.0 --port 8000
```

### 6.2 Required Environment Variables

**Essential:**
```bash
DPO_GATEWAY_SHARED_SECRET=<hmac_secret>  # Required for HMAC verification
```

**For Registration (all required if any present):**
```bash
DPO_PUBLIC_BASE_URL=https://dpo-service.example.com
DPO_REGISTER_URL=https://gateway.example.com/services/register
DPO_REGISTER_SECRET=<registration_secret>
```

### 6.3 Optional Configuration

```bash
# Service Limits
DPO_SERVICE_TTL_SECONDS=21600         # Registration TTL (default: 6 hours)
DPO_MAX_CONCURRENT_JOBS=2             # Worker pool size
DPO_JOB_TIMEOUT_SECONDS=3600          # Max job duration (1 hour)
DPO_MAX_DATASET_SIZE_MB=5             # Max dataset size
DPO_RATE_LIMIT_PER_MINUTE=5           # Per-user rate limit

# CORS (for development/debugging)
DPO_ALLOW_DIRECT_ORIGINS=http://localhost:3000,http://localhost:8080

# Paths
DPO_WORKING_DIR=/app                  # Working directory
DPO_CACHE_DIR=/app/.cache             # Cache directory
```

### 6.4 Health Monitoring

- Use `/health` endpoint for liveness/readiness probes
- Check `queue_stats` for queue depth and job status distribution
- Monitor `uptime_s` for service stability

### 6.5 Idempotency

- Support via `Idempotency-Key` header
- Duplicate requests with same key return original `run_id`
- Keys cached for 10 minutes

## Integration Checklist

1. **Gateway Configuration:**
   - [ ] Set up HMAC signing with shared secret
   - [ ] Implement canonical string generation
   - [ ] Add X-Novalto-User and X-Novalto-Signature headers

2. **Service Registration:**
   - [ ] Configure registration endpoint and secret
   - [ ] Set appropriate TTL for your environment
   - [ ] Handle registration failures gracefully

3. **Request Flow:**
   - [ ] Validate dataset format before sending
   - [ ] Handle rate limiting (429) responses
   - [ ] Implement polling for run status
   - [ ] Respect user ownership rules

4. **Error Handling:**
   - [ ] Handle 401 (auth failure)
   - [ ] Handle 403 (insufficient privileges)
   - [ ] Handle 429 (rate limit)
   - [ ] Handle 413 (payload too large)

5. **Monitoring:**
   - [ ] Set up health checks
   - [ ] Monitor queue depth
   - [ ] Track job success/failure rates

## Example Integration (Python)

```python
import base64
import json
import hashlib
import hmac
import httpx

class DPOServiceClient:
    def __init__(self, base_url: str, shared_secret: str):
        self.base_url = base_url
        self.shared_secret = shared_secret
    
    def _create_signature(self, method: str, path: str, body: bytes, user_claims: dict) -> tuple:
        # Encode user claims
        user_json = json.dumps(user_claims)
        user_b64 = base64.b64encode(user_json.encode()).decode()
        
        # Create canonical string
        body_sha256 = hashlib.sha256(body).hexdigest()
        canonical = f"{method}\n{path}\n{body_sha256}\n{user_b64}"
        
        # Compute signature
        signature = hmac.new(
            self.shared_secret.encode(),
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return user_b64, signature
    
    async def trigger_finetune(self, kb_id: str, exp_name: str, dataset: list):
        user_claims = {
            "uid": "user_123",
            "email": "admin@example.com",
            "admin": True
        }
        
        payload = {
            "kb_id": kb_id,
            "exp_name": exp_name,
            "dataset_inline": dataset
        }
        
        body = json.dumps(payload).encode()
        user_b64, signature = self._create_signature(
            "POST", "/trigger-finetune", body, user_claims
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/trigger-finetune",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Novalto-User": user_b64,
                    "X-Novalto-Signature": signature
                }
            )
            response.raise_for_status()
            return response.json()
```

## Troubleshooting

**401 Unauthorized:**
- Check HMAC signature computation
- Verify shared secret matches
- Ensure canonical string format is exact
- Check Base64 encoding of user claims

**403 Forbidden:**
- Verify `admin: true` in user claims for /trigger-finetune
- Check user ownership for run endpoints

**429 Too Many Requests:**
- Implement backoff strategy
- Check for existing active runs for kb_id
- Respect rate limits (5/min per user)

**500 Internal Server Error:**
- Check service logs
- Verify dataset format
- Ensure required environment variables are set