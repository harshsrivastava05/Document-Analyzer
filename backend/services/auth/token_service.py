import jwt
import os
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from db.utils import ensure_user_exists_optimized
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

def _get_secret():
    secret = os.getenv("JWT_SECRET")
    if not secret:
        logger.warning("⚠️ JWT_SECRET not set! Using fallback for development")
        secret = "fallback-insecure-secret"
    return secret

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=["HS256"])
        user_id = payload.get("userId") or payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=403, detail="Invalid token payload")
        ensure_user_exists_optimized(user_id)
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid token")

def create_access_token(user_id: str, expires_delta: timedelta = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode = {"userId": user_id, "user_id": user_id, "iat": datetime.utcnow(), "exp": expire}
    return jwt.encode(to_encode, _get_secret(), algorithm="HS256")