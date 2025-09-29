from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor
from services.auth_service import get_current_user
from services.gcs_service import gcs_service
from database import get_db_connection
from models.schemas import DocumentResponse
from typing import List
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/documents")
async def get_user_documents(
    user_id: str = Depends(get_current_user),
    userId: str = Query(None)  # Support both methods for compatibility
):
    """Get all documents for the current user"""
    try:
        # Use userId from query param if provided (for frontend compatibility)
        final_user_id = userId if userId else user_id
        
        with get_db_connection() as connection:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute('''
                SELECT id, title, gcs_file_id, mime_type, file_size, summary, created_at, updated_at
                FROM documents 
                WHERE user_id = %s 
                ORDER BY created_at DESC
            ''', (final_user_id,))
            
            documents = cursor.fetchall()
            cursor.close()
            
            # Format documents for response
            formatted_documents = []
            for doc in documents:
                formatted_documents.append({
                    "id": doc["id"],
                    "title": doc["title"],
                    "gcs_file_id": doc["gcs_file_id"],
                    "mime_type": doc["mime_type"],
                    "file_size": doc["file_size"],
                    "summary": doc["summary"],
                    "created_at": doc["created_at"].isoformat() if doc["created_at"] else None,
                    "updated_at": doc["updated_at"].isoformat() if doc["updated_at"] else None
                })
            
            return {"documents": formatted_documents}
        
    except Exception as e:
        logger.error(f"Failed to fetch documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")

@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """Download a document"""
    try:
        # Verify user owns the document
        with get_db_connection() as connection:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute('''
                SELECT gcs_file_id, title, mime_type 
                FROM documents 
                WHERE id = %s AND user_id = %s
            ''', (document_id, user_id))
            
            document = cursor.fetchone()
            cursor.close()
            
            if not document:
                raise HTTPException(status_code=404, detail="Document not found")
            
            # Download from GCS
            file_content = gcs_service.download_file(document['gcs_file_id'], user_id)
            
            from fastapi.responses import Response
            mime_type = document['mime_type'] or 'application/pdf'
            # Force inline so PDFs render in iframe/viewers
            headers = {
                "Content-Disposition": f"inline; filename=\"{document['title']}\""
            }
            return Response(
                content=file_content,
                media_type=mime_type,
                headers=headers
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """Delete a document"""
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            # Get document info
            cursor.execute('''
                SELECT gcs_file_id FROM documents 
                WHERE id = %s AND user_id = %s
            ''', (document_id, user_id))
            
            document = cursor.fetchone()
            
            if not document:
                cursor.close()
                raise HTTPException(status_code=404, detail="Document not found")
            
            # Delete from GCS
            gcs_service.delete_file(document['gcs_file_id'], user_id)
            
            # Delete from database (CASCADE will handle qnas)
            cursor.execute('DELETE FROM documents WHERE id = %s AND user_id = %s', (document_id, user_id))
            cursor.close()
            connection.commit()
            
            return {"success": True, "message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")