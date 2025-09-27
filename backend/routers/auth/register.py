from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional   # <-- add this line
from db.connection import get_db_connection
from services.auth.password_service import get_password_hash
from services.auth.token_service import create_access_token
from datetime import timedelta
import uuid
import logging


router = APIRouter()
logger = logging.getLogger(__name__)

class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
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


def generate_cuid() -> str:
    return str(uuid.uuid4()).replace('-', '')[:25]

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    try:
        with get_db_connection() as connection:
            cur = connection.cursor()

            # Ensure not exists
            cur.execute('SELECT id FROM "users" WHERE email=%s', (request.email,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Email already registered")

            user_id = generate_cuid()
            if _users_has_password_hash():
                if not request.password:
                    raise HTTPException(status_code=400, detail="Password required")
                pwd_hash = get_password_hash(request.password)
                cur.execute(
                    'INSERT INTO "users" (id, email, name, password_hash, created_at, updated_at) VALUES (%s,%s,%s,%s,NOW(),NOW())',
                    (user_id, request.email, request.name, pwd_hash)
                )
            else:
                cur.execute(
                    'INSERT INTO "users" (id, email, name, created_at, updated_at) VALUES (%s,%s,%s,NOW(),NOW())',
                    (user_id, request.email, request.name)
                )
            connection.commit()

            token = create_access_token(user_id=user_id, expires_delta=timedelta(hours=24))
            return TokenResponse(access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")