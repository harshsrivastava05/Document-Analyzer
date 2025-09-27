from fastapi import APIRouter, Depends, HTTPException
from services.auth.token_service import get_current_user
from services.storage.gcs_service import gcs_service
from db.connection import get_db_connection

router = APIRouter()

@router.delete("/{document_id}")
async def delete_document(document_id: str, user_id: str = Depends(get_current_user)):
    with get_db_connection() as connection:
        cur = connection.cursor()
        cur.execute('SELECT gcs_file_id FROM "documents" WHERE id=%s AND user_id=%s', (document_id, user_id))
        doc = cur.fetchone()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        gcs_service.delete_file(doc['gcs_file_id'], user_id)
        cur.execute('DELETE FROM "documents" WHERE id=%s AND user_id=%s', (document_id, user_id))
        connection.commit()
        return {"success": True}