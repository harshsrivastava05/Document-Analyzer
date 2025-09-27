from fastapi import APIRouter, Depends, Query, HTTPException
from services.auth.token_service import get_current_user
from db.connection import get_db_connection
import logging


router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/")
async def get_user_documents(user_id: str = Depends(get_current_user), userId: str = Query(None)):
    final_user_id = userId if userId else user_id
    try:
        with get_db_connection() as connection:
            cur = connection.cursor()
            cur.execute('''
                SELECT id, title, gcs_file_id, mime_type, file_size, summary, created_at, updated_at
                FROM "documents" WHERE user_id=%s ORDER BY created_at DESC
            ''', (final_user_id,))
            docs = cur.fetchall()
            return {"documents": docs}
    except Exception as e:
        logger.error(f"Fetch documents failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch documents")