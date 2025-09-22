import jwt
import os
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _get_jwt_secret():
    """Get JWT secret with fallback"""
    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        # Generate a warning but use a fallback for development
        print("⚠️  WARNING: JWT_SECRET not set! Using insecure fallback for development")
        jwt_secret = "fallback-insecure-secret-only-for-development-please-set-jwt-secret"
    return jwt_secret

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Validate JWT token and return user_id"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_access_token(user_id: str, expires_delta: timedelta = None) -> str:
    """Create a new access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode = {"user_id": user_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, _get_jwt_secret(), algorithm="HS256")
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)