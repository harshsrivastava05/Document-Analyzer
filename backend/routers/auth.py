from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.auth_service import create_access_token, verify_password, get_password_hash
from database import get_db_connection
import uuid
from datetime import timedelta

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """User login"""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM users WHERE email = %s", (request.email,))
        user = cursor.fetchone()
        
        if not user or not verify_password(request.password, user.get('password_hash', '')):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        access_token = create_access_token(
            user_id=user['id'],
            expires_delta=timedelta(hours=24)
        )
        
        return TokenResponse(access_token=access_token)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
    finally:
        if connection and connection.is_connected():
            connection.close()

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """User registration"""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (request.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user
        user_id = str(uuid.uuid4())
        password_hash = get_password_hash(request.password)
        
        cursor.execute("""
            INSERT INTO users (id, email, name, password_hash)
            VALUES (%s, %s, %s, %s)
        """, (user_id, request.email, request.name, password_hash))
        
        connection.commit()
        
        access_token = create_access_token(
            user_id=user_id,
            expires_delta=timedelta(hours=24)
        )
        
        return TokenResponse(access_token=access_token)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    finally:
        if connection and connection.is_connected():
            connection.close()