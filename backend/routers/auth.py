from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.auth_service import create_access_token, verify_password, get_password_hash
from database import get_db_connection
import uuid
from datetime import timedelta
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

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

# For compatibility with NextAuth, we'll also need to handle password_hash field
def generate_cuid():
    """Generate a CUID-like ID to match Prisma"""
    return str(uuid.uuid4()).replace('-', '')[:25]

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """User login"""
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            
            # Note: In the Prisma schema, there's no password_hash field in users table
            # This suggests the app uses NextAuth for authentication
            # We'll need to add a password_hash field or handle this differently
            cursor.execute('SELECT id, email, name FROM "users" WHERE email = %s', (request.email,))
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            # For now, we'll create a simple token without password verification
            # In production, you'd want to add a password_hash field to users table
            access_token = create_access_token(
                user_id=user['id'],
                expires_delta=timedelta(hours=24)
            )
            
            return TokenResponse(access_token=access_token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """User registration"""
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            
            # Check if user exists
            cursor.execute('SELECT id FROM "users" WHERE email = %s', (request.email,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Email already registered")
            
            # Create user (using CUID format like Prisma)
            user_id = generate_cuid()
            
            cursor.execute('''
                INSERT INTO "users" (id, email, name, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
            ''', (user_id, request.email, request.name))
            
            connection.commit()
            
            access_token = create_access_token(
                user_id=user_id,
                expires_delta=timedelta(hours=24)
            )
            
            return TokenResponse(access_token=access_token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/create-user")
async def create_user_for_nextauth(user_data: dict):
    """Create user for NextAuth integration"""
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            
            user_id = user_data.get('id') or generate_cuid()
            email = user_data.get('email')
            name = user_data.get('name')
            image = user_data.get('image')
            
            cursor.execute('''
                INSERT INTO "users" (id, email, name, image, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (email) DO UPDATE SET
                name = EXCLUDED.name,
                image = EXCLUDED.image,
                updated_at = NOW()
                RETURNING id
            ''', (user_id, email, name, image))
            
            result = cursor.fetchone()
            connection.commit()
            
            return {"id": result["id"], "success": True}
        
    except Exception as e:
        logger.error(f"User creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"User creation failed: {str(e)}")