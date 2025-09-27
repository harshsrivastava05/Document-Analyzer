from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from db.connection import get_db_connection
from services.auth.password_service import verify_password
from services.auth.token_service import create_access_token
from typing import Optional
import logging
from datetime import timedelta
from typing import Optional

router = APIRouter()
logger = logging.getLogger(__name__)

class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _users_has_password_hash() -> bool:
    try:
        with get_db_connection() as connection:
            cur = connection.cursor()
            cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name='users' AND column_name='password_hash'
                LIMIT 1
                """
            )
            return cur.fetchone() is not None
    except Exception as e:
        logger.warning(f"Could not check password_hash column: {e}")
        return False

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Production-ready login.
    - If users.password_hash exists: verify password.
    - Else: reject password login and ask to use OAuth/NextAuth (email-only).
    """
    try:
        with get_db_connection() as connection:
            cur = connection.cursor()
            cur.execute('SELECT id, email, name{ph} FROM "users" WHERE email=%s'.format(
                ph=", password_hash" if _users_has_password_hash() else ""
            ), (request.email,))
            user = cur.fetchone()
            if not user:
                raise HTTPException(status_code=401, detail="Invalid credentials")

            # Password flow only if column exists
            if _users_has_password_hash():
                if not request.password:
                    raise HTTPException(status_code=400, detail="Password required")
                stored_hash = user.get('password_hash')  # RealDictCursor expected
                if not stored_hash or not verify_password(request.password, stored_hash):
                    raise HTTPException(status_code=401, detail="Invalid credentials")
            else:
                # No password column -> treat as OAuth-only project
                if request.password:
                    raise HTTPException(status_code=400, detail="Password login not enabled for this project")

            token = create_access_token(user_id=user['id'], expires_delta=timedelta(hours=24))
            return TokenResponse(access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Login failed")