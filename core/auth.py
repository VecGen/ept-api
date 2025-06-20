"""
Authentication utilities for the Developer Efficiency Tracker API
"""

from datetime import datetime, timedelta
from typing import Optional
import hashlib
import jwt
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import get_settings

security = HTTPBearer(auto_error=False)  # Don't auto-error to handle OPTIONS manually


def get_admin_password_hash() -> str:
    """Get the admin password hash"""
    settings = get_settings()
    return hashlib.sha256(settings.admin_password.encode()).hexdigest()


def verify_admin_password(password: str) -> bool:
    """Verify admin password"""
    input_hash = hashlib.sha256(password.encode()).hexdigest()
    return input_hash == get_admin_password_hash()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    settings = get_settings()
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token - skip for OPTIONS requests"""
    # Skip authentication for OPTIONS (CORS preflight) requests
    if request.method == "OPTIONS":
        print("🔧 Skipping authentication for OPTIONS request")
        return {"user_type": "options", "sub": "preflight"}
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        print(f"🔑 Token verified successfully for user: {payload.get('sub')}")
        return payload
    except jwt.PyJWTError as e:
        print(f"❌ Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_admin_token(token_data: dict = Depends(verify_token)) -> dict:
    """Verify admin access token"""
    # Allow OPTIONS requests to pass through
    if token_data.get("user_type") == "options":
        return token_data
        
    if token_data.get("user_type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return token_data


def verify_engineer_token(token_data: dict = Depends(verify_token)) -> dict:
    """Verify engineer access token"""
    # Allow OPTIONS requests to pass through
    if token_data.get("user_type") == "options":
        return token_data
        
    if token_data.get("user_type") not in ["admin", "engineer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Engineer or admin access required"
        )
    return token_data 