# DPO Microservice - Gateway Alignment Summary

## Changes Made

### 1. HMAC Header Case Sensitivity Fix ✅
**File:** `core/auth.py` (Lines 115-116)

**Before:**
```python
user_header = request.headers.get("X-Novalto-User")
signature = request.headers.get("X-Novalto-Signature")
```

**After:**
```python
# Accept both lowercase (x-novalto-*) and uppercase (X-Novalto-*) variants
user_header = request.headers.get("x-novalto-user") or request.headers.get("X-Novalto-User")
signature = request.headers.get("x-novalto-signature") or request.headers.get("X-Novalto-Signature")
```

**Result:** Service now accepts headers in either case:
- `x-novalto-user` and `x-novalto-signature` (lowercase - gateway preferred)
- `X-Novalto-User` and `X-Novalto-Signature` (uppercase - legacy)

## Verification of Existing Compliance

### 2. Trigger Request Schema ✅ ALREADY COMPLIANT
**File:** `webhook_handler.py` (TriggerFinetuneRequest class)

✅ **Required fields:** `kb_id`, `exp_name`  
✅ **Optional with defaults:** `base_model` (default: "zephyr"), `algo` (default: "dpo")  
✅ **Dataset XOR validation:** Must provide exactly one of `dataset_inline` OR `dataset_url`  
✅ **Inline dataset structure:** Array of `{prompt, chosen, rejected}` records  
✅ **URL validation:** Must use https:// or http://  

### 3. Response Formats ✅ ALREADY COMPLIANT
**Trigger Response:**
```json
{
  "run_id": "uuid-string",
  "status": "queued"
}
```

**Run Status Response:**
```json
{
  "run_id": "uuid-string",
  "status": "queued|running|completed|failed|cancelled",
  "metrics": {...},        // Optional
  "started_at": 1234567,   // Unix timestamp, optional
  "finished_at": 1234567   // Unix timestamp, optional
}
```

**Artifacts Response:**
```json
{
  "checkpoint_url": "https://...",  // Optional
  "report_url": "https://...",      // Optional
  "logs_url": "https://..."         // Optional
}
```

### 4. Status Vocabulary ✅ ALREADY COMPLIANT
**Canonical Status Values (RunStatus enum):**
- `queued` - Job waiting in queue
- `running` - Job actively processing
- `completed` - Job finished successfully (NOT "succeeded")
- `failed` - Job failed with error
- `cancelled` - Job cancelled by user/system

### 5. Error Handling ✅ ALREADY COMPLIANT
✅ **401 Unauthorized:** Invalid/missing HMAC signature or malformed user claims  
✅ **403 Forbidden:** Valid HMAC but `admin=false` when admin required  
✅ **429 Too Many Requests:** Rate limit exceeded or active job exists for kb_id  
✅ **400 Bad Request:** Invalid dataset format or missing required fields  
✅ **413 Payload Too Large:** Dataset >5MB (configurable via `DPO_MAX_DATASET_SIZE_MB`)  

### 6. Registration ✅ ALREADY COMPLIANT
**Registration Payload:**
```json
{
  "base_url": "https://service.example.com",
  "version": "1.0.0",
  "ttl_seconds": 21600
}
```

**Registration Headers:** Sends `X-DPO-Register-Secret` (uppercase - this is fine)

### 7. Dataset Limits & Formats ✅ ALREADY COMPLIANT
✅ **Inline size limit:** 5MB (configurable)  
✅ **URL formats:** .json, .jsonl, .jsonl.gz supported  
✅ **Timeout:** 60 seconds for URL fetches  
✅ **Validation:** All fields (prompt, chosen, rejected) required and non-empty  

### 8. Idempotency & Rate Limits ✅ ALREADY COMPLIANT
✅ **Idempotency-Key header:** Supported, cached for 10 minutes  
✅ **Per-user rate limit:** 5 requests per minute (configurable)  
✅ **Per-kb_id limit:** 1 active training job at a time  
✅ **429 responses:** Returned on rate limit violations  

## Testing

### Test Script Created
**File:** `test_header_case.py`

The test script verifies:
- Lowercase header acceptance: `x-novalto-user`, `x-novalto-signature`
- Uppercase header acceptance: `X-Novalto-User`, `X-Novalto-Signature`
- Mixed case scenarios
- Proper 401 responses for missing headers
- Health endpoint functionality

**To run tests:**
```bash
# Start the service first
uvicorn webhook_handler:app --host 0.0.0.0 --port 8000

# In another terminal, run the test
python3 test_header_case.py
```

## Environment Configuration

### Required for Gateway Integration:
```bash
DPO_GATEWAY_SHARED_SECRET=<hmac_secret>     # Required for HMAC verification
```

### Optional for Service Registration:
```bash
DPO_PUBLIC_BASE_URL=https://dpo-service.example.com
DPO_REGISTER_URL=https://gateway.example.com/services/register
DPO_REGISTER_SECRET=<registration_secret>
```

## Summary

✅ **Headers:** Now accepts both lowercase and uppercase variants  
✅ **Schema:** Already compliant with exact gateway specification  
✅ **Responses:** Already using correct format and status vocabulary  
✅ **Error codes:** Already returns proper HTTP status codes  
✅ **Limits:** Already enforces 5MB dataset limit and rate limiting  
✅ **Registration:** Already sends correct payload with TTL renewal  

**The DPO microservice is now fully aligned with gateway requirements.**