"""
Authentication and authorization for the DPO microservice.

Handles HMAC signature verification for gateway-signed requests and 
provides middleware for protecting endpoints.
"""

import base64
import hashlib
import hmac
import json
import logging
from typing import Optional, Dict, Any

from fastapi import HTTPException, Request
from pydantic import BaseModel

from .config import get_config


logger = logging.getLogger(__name__)


class UserClaims(BaseModel):
    """
    User claims passed from the gateway via X-Novalto-User header.
    
    The gateway determines how admin:true is set - it may use a custom claim
    like customClaims.admin or an email allowlist. This microservice only
    checks that admin:true is present in the claims for protected endpoints.
    """
    uid: str
    email: str
    admin: bool  # Set by gateway based on allowlist OR custom claim


def create_canonical_string(method: str, path: str, body_sha256: str, user_header: str) -> str:
    """Create canonical string for HMAC signature verification."""
    return f"{method}\n{path}\n{body_sha256}\n{user_header}"


def compute_hmac_signature(canonical_string: str, secret: str) -> str:
    """Compute HMAC-SHA256 signature for the canonical string."""
    return hmac.new(
        secret.encode('utf-8'),
        canonical_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def verify_gateway_signature(
    method: str,
    path: str, 
    body: bytes,
    user_header: str,
    signature: str,
    secret: str
) -> bool:
    """Verify HMAC signature from gateway."""
    try:
        # Compute body SHA256
        body_sha256 = hashlib.sha256(body).hexdigest()
        
        # Create canonical string
        canonical = create_canonical_string(method, path, body_sha256, user_header)
        
        # Compute expected signature
        expected_signature = compute_hmac_signature(canonical, secret)
        
        # Compare signatures (constant time)
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        logger.warning(f"Signature verification error: {e}")
        return False


def parse_user_claims(user_header: str) -> Optional[UserClaims]:
    """Parse base64-encoded user claims from gateway header."""
    try:
        # Decode base64
        decoded_bytes = base64.b64decode(user_header)
        decoded_str = decoded_bytes.decode('utf-8')
        
        # Parse JSON
        claims_data = json.loads(decoded_str)
        
        return UserClaims(**claims_data)
        
    except Exception as e:
        logger.warning(f"Failed to parse user claims: {e}")
        return None


async def verify_request_auth(request: Request, require_admin: bool = True) -> UserClaims:
    """
    Verify request authentication using gateway headers.
    
    Returns 401 for invalid/missing HMAC signature or malformed user claims.
    Returns 403 for valid HMAC but admin=false when admin is required.
    
    Args:
        request: FastAPI request object
        require_admin: Whether to require admin privileges
        
    Returns:
        UserClaims object with verified user information
        
    Raises:
        HTTPException: 401 for auth failures, 403 for authorization failures
    """
    config = get_config()
    
    # Get required headers
    user_header = request.headers.get("X-Novalto-User")
    signature = request.headers.get("X-Novalto-Signature")
    
    if not user_header or not signature:
        logger.warning("Missing authentication headers")
        raise HTTPException(
            status_code=401,
            detail="Missing authentication headers"
        )
    
    # Get request body
    body = await request.body()
    
    # Debug logging
    logger.debug(f"Request method: {request.method}")
    logger.debug(f"Request path: {request.url.path}")
    logger.debug(f"Request body length: {len(body)}")
    logger.debug(f"User header (first 50): {user_header[:50]}...")
    logger.debug(f"Signature (first 20): {signature[:20]}...")
    
    # Verify signature
    is_valid = verify_gateway_signature(
        method=request.method,
        path=request.url.path,
        body=body,
        user_header=user_header,
        signature=signature,
        secret=config.gateway_shared_secret
    )
    
    if not is_valid:
        logger.warning(f"Invalid signature for request to {request.url.path}")
        logger.debug(f"Expected body SHA256: {hashlib.sha256(body).hexdigest()}")
        raise HTTPException(
            status_code=401,
            detail="Invalid signature"
        )
    
    # Parse user claims
    user_claims = parse_user_claims(user_header)
    if not user_claims:
        logger.warning("Failed to parse user claims")
        raise HTTPException(
            status_code=401,
            detail="Invalid user claims"
        )
    
    # Check admin requirement
    if require_admin and not user_claims.admin:
        logger.warning(f"Non-admin user {user_claims.uid} attempted admin action")
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    
    logger.info(f"Authenticated user {user_claims.uid} (admin: {user_claims.admin})")
    return user_claims


async def extract_user_claims(request: Request) -> Optional[UserClaims]:
    """
    Extract user claims without failing on invalid auth.
    Used for optional authentication scenarios.
    """
    try:
        return await verify_request_auth(request, require_admin=False)
    except HTTPException:
        return None