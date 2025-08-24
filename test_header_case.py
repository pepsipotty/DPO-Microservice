#!/usr/bin/env python3
"""
Test script to verify header case insensitivity for DPO microservice.
"""

import base64
import hashlib
import hmac
import json
import httpx
import asyncio
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
SHARED_SECRET = "test-secret-123"  # This should match DPO_GATEWAY_SHARED_SECRET

def create_hmac_signature(method: str, path: str, body: bytes, user_claims: Dict[str, Any]) -> tuple:
    """Create HMAC signature and base64-encoded user header."""
    # Encode user claims
    user_json = json.dumps(user_claims)
    user_b64 = base64.b64encode(user_json.encode()).decode()
    
    # Create canonical string
    body_sha256 = hashlib.sha256(body).hexdigest()
    canonical = f"{method}\n{path}\n{body_sha256}\n{user_b64}"
    
    print(f"Canonical string:\n{repr(canonical)}")
    
    # Compute signature
    signature = hmac.new(
        SHARED_SECRET.encode(),
        canonical.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return user_b64, signature

async def test_header_cases():
    """Test different header case combinations."""
    
    user_claims = {
        "uid": "test_user_123",
        "email": "test@example.com",
        "admin": True
    }
    
    test_payload = {
        "kb_id": "test_kb_001",
        "exp_name": "test_experiment",
        "dataset_inline": [
            {
                "prompt": "What is AI?",
                "chosen": "AI is artificial intelligence",
                "rejected": "AI is nothing"
            }
        ]
    }
    
    body = json.dumps(test_payload).encode()
    user_b64, signature = create_hmac_signature("POST", "/trigger-finetune", body, user_claims)
    
    # Test cases with different header combinations
    test_cases = [
        {
            "name": "Lowercase headers",
            "headers": {
                "content-type": "application/json",
                "x-novalto-user": user_b64,
                "x-novalto-signature": signature
            }
        },
        {
            "name": "Uppercase headers",
            "headers": {
                "Content-Type": "application/json",
                "X-Novalto-User": user_b64,
                "X-Novalto-Signature": signature
            }
        },
        {
            "name": "Mixed case headers",
            "headers": {
                "Content-Type": "application/json",
                "x-novalto-user": user_b64,
                "X-Novalto-Signature": signature
            }
        }
    ]
    
    async with httpx.AsyncClient() as client:
        for test_case in test_cases:
            print(f"\n--- Testing: {test_case['name']} ---")
            try:
                response = await client.post(
                    f"{BASE_URL}/trigger-finetune",
                    content=body,
                    headers=test_case["headers"],
                    timeout=10.0
                )
                
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text}")
                
                if response.status_code == 200:
                    print("✅ SUCCESS: Headers accepted")
                elif response.status_code == 401:
                    print("❌ FAILED: Authentication failed (401)")
                elif response.status_code == 403:
                    print("❌ FAILED: Authorization failed (403)")
                else:
                    print(f"❌ FAILED: Unexpected status {response.status_code}")
                    
            except Exception as e:
                print(f"❌ ERROR: {e}")

async def test_health_endpoint():
    """Test health endpoint (no auth required)."""
    print("\n--- Testing Health Endpoint ---")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Service healthy, version: {data.get('version')}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Cannot connect to service: {e}")
            print("Make sure the DPO service is running on localhost:8000")

async def test_auth_failures():
    """Test authentication failure scenarios."""
    print("\n--- Testing Auth Failure Cases ---")
    
    test_cases = [
        {
            "name": "Missing headers",
            "headers": {"Content-Type": "application/json"}
        },
        {
            "name": "Missing user header",
            "headers": {
                "Content-Type": "application/json",
                "x-novalto-signature": "dummy-signature"
            }
        },
        {
            "name": "Missing signature header",
            "headers": {
                "Content-Type": "application/json",
                "x-novalto-user": "dummy-user"
            }
        }
    ]
    
    async with httpx.AsyncClient() as client:
        for test_case in test_cases:
            print(f"\n{test_case['name']}:")
            try:
                response = await client.post(
                    f"{BASE_URL}/trigger-finetune",
                    json={"kb_id": "test", "exp_name": "test"},
                    headers=test_case["headers"],
                    timeout=5.0
                )
                
                if response.status_code == 401:
                    print("✅ Correctly returned 401 Unauthorized")
                else:
                    print(f"❌ Expected 401, got {response.status_code}")
                    
            except Exception as e:
                print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    print("DPO Microservice Header Case Testing")
    print("=====================================")
    
    asyncio.run(test_health_endpoint())
    asyncio.run(test_auth_failures())
    asyncio.run(test_header_cases())