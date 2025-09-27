from fastapi import APIRouter, Depends, HTTPException
from services.auth.token_service import get_current_user
from services.storage.gcs_service import gcs_service
from db.connection import get_db_connection
from typing import Optional

router = APIRouter()

@router.get("/{document_id}/download")
async def download_document(document_id: str, user_id: str = Depends(get_current_user)):
    with get_db_connection() as connection:
        cur = connection.cursor()
        cur.execute('SELECT gcs_file_id, title, mime_type FROM "documents" WHERE id=%s AND user_id=%s', (document_id, user_id))
        doc = cur.fetchone()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        content = gcs_service.download_file(doc['gcs_file_id'], user_id)
        from fastapi.responses import Response
        return Response(content=content, media_type=doc['mime_type'] or 'application/octet-stream', headers={"Content-Disposition": f"attachment; filename={doc['title']}"})
