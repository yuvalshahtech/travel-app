"""
JWT Authentication Utilities

Provides token generation, validation, and user extraction for secure API endpoints.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Security scheme for JWT token extraction
security = HTTPBearer()


def get_secret_key():
    """
    Get JWT secret key from environment at runtime (not import time).
    This ensures .env is loaded before the key is read.
    """
    secret = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
    import sys
    print(f"[JWT] SECRET_KEY loaded at runtime: {secret[:20]}... (length: {len(secret)})", file=sys.stderr)
    return secret


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a JWT access token.
    
    Args:
        data: Dictionary containing claims (e.g., {"sub": user_id, "email": email})
        expires_delta: Token expiration time (default: 24 hours)
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        import sys
        secret = get_secret_key()
        print(f"[JWT] Verifying token with SECRET_KEY: {secret[:20]}...", file=sys.stderr)
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        print(f"[JWT] Token verified successfully. sub={payload.get('sub')}, email={payload.get('email')}", file=sys.stderr)
        return payload
    except JWTError as e:
        import sys
        print(f"[JWT] Token verification failed: {str(e)}", file=sys.stderr)
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """
    Extract user ID from JWT token (FastAPI dependency).
    
    Use this as a dependency in protected routes:
    @router.get("/protected")
    def protected_route(user_id: int = Depends(get_current_user_id)):
        # user_id is extracted from JWT token
        pass
    
    Args:
        credentials: HTTP Authorization credentials (automatically injected by FastAPI)
    
    Returns:
        User ID extracted from token (as integer)
    
    Raises:
        HTTPException: If token is invalid or user_id not found
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    # JWT spec requires 'sub' to be a STRING
    # Extract as string, then convert to int
    sub = payload.get("sub")
    
    if sub is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token: missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = int(sub)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid token: invalid user ID format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


def get_current_user_email(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Extract user email from JWT token (FastAPI dependency).
    
    Args:
        credentials: HTTP Authorization credentials
    
    Returns:
        User email extracted from token
    
    Raises:
        HTTPException: If token is invalid or email not found
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    email = payload.get("email")
    
    if not email:
        raise HTTPException(
            status_code=401,
            detail="Invalid token: missing email",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return email
