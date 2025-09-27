from fastapi import APIRouter, Depends
from services.auth.token_service import get_current_user
from db.connection import get_db_connection

router = APIRouter()

@router.get("/me")
async def get_profile(user_id: str = Depends(get_current_user)):
    with get_db_connection() as connection:
        cur = connection.cursor()
        cur.execute('SELECT id, email, name, image, created_at FROM "users" WHERE id=%s', (user_id,))
        user = cur.fetchone()
        return user or {"id": user_id}