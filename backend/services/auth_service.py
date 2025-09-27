# backend/services/auth_service.py - FIXED VERSION
import jwt
import os
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from typing import Optional
import logging
from database import get_db_connection
from psycopg2.extras import RealDictCursor
import uuid

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _get_jwt_secret():
    """Get JWT secret with fallback"""
    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        logger.warning("⚠️  JWT_SECRET not set! Using insecure fallback for development")
        jwt_secret = "fallback-insecure-secret-only-for-development-please-set-jwt-secret"
    return jwt_secret

def ensure_user_exists(user_id: str) -> bool:
    """Ensure user exists in database - FIXED with proper connection handling"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            with get_db_connection() as connection:
                with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    
                    # Check if user exists
                    cursor.execute('SELECT id FROM "users" WHERE id = %s', (user_id,))
                    user = cursor.fetchone()
                    
                    if user:
                        logger.debug(f"✅ User {user_id[:8]}... already exists in database")
                        return True
                    
                    # Create user if doesn't exist (minimal record)
                    cursor.execute('''
                        INSERT INTO "users" (id, created_at, updated_at)
                        VALUES (%s, NOW(), NOW())
                        ON CONFLICT (id) DO NOTHING
                    ''', (user_id,))
                    
                    # Commit the transaction
                    connection.commit()
                    logger.info(f"✅ Created minimal user record for {user_id[:8]}...")
                    return True
                    
        except Exception as e:
            logger.warning(f"🔄 Failed to ensure user exists (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error(f"❌ Failed to ensure user {user_id[:8]}... exists after {max_retries} attempts: {e}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to initialize user: {str(e)}"
                )
    
    return False

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """Validate JWT token and return user_id with user existence verification"""
    
    if not credentials:
        logger.warning("No authorization credentials provided")
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    token = credentials.credentials
    jwt_secret = _get_jwt_secret()
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        logger.debug(f"JWT payload decoded: {list(payload.keys())}")
        
        # Try both userId and user_id for compatibility
        user_id = payload.get("userId") or payload.get("user_id")
        
        if not user_id:
            logger.error(f"No user ID found in token payload keys: {list(payload.keys())}")
            raise HTTPException(status_code=403, detail="Invalid token payload - no user ID")
        
        # CRITICAL FIX: Ensure user exists in database before proceeding
        try:
            ensure_user_exists(user_id)
        except HTTPException as e:
            # Re-raise HTTP exceptions
            raise e
        except Exception as e:
            logger.error(f"❌ Failed to ensure user exists: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize user")
            
        logger.debug(f"✅ Authenticated user: {user_id[:8]}...")
        return user_id
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise HTTPException(status_code=403, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(status_code=403, detail="Invalid token")
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
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

# Helper function to generate CUID-like IDs
def generate_cuid():
    """Generate a CUID-like ID to match Prisma format"""
    return str(uuid.uuid4()).replace('-', '')[:25]