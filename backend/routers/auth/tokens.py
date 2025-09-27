from fastapi import APIRouter, Depends, HTTPException
from services.auth.token_service import get_current_user, create_access_token
from datetime import timedelta

router = APIRouter()

@router.post("/refresh")
async def refresh_token(user_id: str = Depends(get_current_user)):
    try:
        return {"access_token": create_access_token(user_id, expires_delta=timedelta(hours=24))}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to refresh token")
