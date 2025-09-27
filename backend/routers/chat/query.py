from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth.token_service import get_current_user
from services.ai_services import ai_services
from db.connection import get_db_connection
from psycopg2.extras import RealDictCursor
from datetime import datetime
import uuid
import logging


router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/ask")
async def ask_question(question: str, docId: str = Query(...), user_id: str = Depends(get_current_user)):
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute('SELECT id FROM "documents" WHERE id=%s AND user_id=%s', (docId, user_id))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Document not found")

            rag_response = await ai_services.query_rag(question, docId)

            # Persist conversation
            uid1 = str(uuid.uuid4())
            uid2 = str(uuid.uuid4())
            now = datetime.utcnow()
            cursor.execute('INSERT INTO "qnas" (id, user_id, document_id, role, content, created_at) VALUES (%s,%s,%s,%s,%s,%s)',
                           (uid1, user_id, docId, 'user', question, now))
            cursor.execute('INSERT INTO "qnas" (id, user_id, document_id, role, content, created_at) VALUES (%s,%s,%s,%s,%s,%s)',
                           (uid2, user_id, docId, 'assistant', rag_response.get("answer",""), now))
            connection.commit()
            return {
                "id": uid2,
                "role": "assistant",
                "content": rag_response.get("answer",""),
                "sources": rag_response.get("sources", []),
                "confidence": rag_response.get("confidence", 0.0),
                "created_at": now
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Question failed: {e}")
        raise HTTPException(status_code=500, detail="Question processing failed")
