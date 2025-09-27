import jwt
import os
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from typing import Optional
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)  # Don't auto-error, let us handle it
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _get_jwt_secret():
    """Get JWT secret with fallback"""
    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        # Generate a warning but use a fallback for development
        logger.warning("⚠️  JWT_SECRET not set! Using insecure fallback for development")
        jwt_secret = "fallback-insecure-secret-only-for-development-please-set-jwt-secret"
    return jwt_secret

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """Validate JWT token and return user_id - compatible with frontend JWT format"""
    
    if not credentials:
        logger.warning("No authorization credentials provided")
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    token = credentials.credentials
    jwt_secret = _get_jwt_secret()
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        logger.debug(f"JWT payload decoded: {list(payload.keys())}")
        
        # Try both userId and user_id for compatibility with different JWT formats
        user_id = payload.get("userId") or payload.get("user_id")
        
        if not user_id:
            logger.error(f"No user ID found in token payload keys: {list(payload.keys())}")
            raise HTTPException(status_code=403, detail="Invalid token payload - no user ID")
            
        logger.info(f"✅ Authenticated user: {user_id[:8]}...")
        return user_id
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise HTTPException(status_code=403, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(status_code=403, detail="Invalid token")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=403, detail="Authentication failed")

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    """Optional authentication - returns None if no valid token"""
    try:
        if not credentials:
            return None
        return get_current_user(credentials)
    except HTTPException:
        return None

def create_access_token(user_id: str, expires_delta: timedelta = None) -> str:
    """Create a new access token - compatible with frontend format"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    # Create payload compatible with frontend expectations
    to_encode = {
        "userId": user_id,      # Frontend expects this
        "user_id": user_id,     # Backend compatibility
        "iat": datetime.utcnow(),
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, _get_jwt_secret(), algorithm="HS256")
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)