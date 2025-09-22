from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth_service import get_current_user
from services.gcs_service import gcs_service
from database import get_db_connection
from models.schemas import DocumentResponse
from typing import List
import json

router = APIRouter()

@router.get("/documents")
async def get_user_documents(
    user_id: str = Depends(get_current_user),
    userId: str = Query(None)  # Support both methods for compatibility
):
    """Get all documents for the current user"""
    connection = None
    try:
        # Use userId from query param if provided (for frontend compatibility)
        final_user_id = userId if userId else user_id
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, title, gcs_file_id, mime_type, file_size, summary, created_at, updated_at
            FROM documents 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """, (final_user_id,))
        
        documents = cursor.fetchall()
        
        return {"documents": documents}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")
    finally:
        if connection and connection.is_connected():
            connection.close()

@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """Download a document"""
    connection = None
    try:
        # Verify user owns the document
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT gcs_file_id, title, mime_type 
            FROM documents 
            WHERE id = %s AND user_id = %s
        """, (document_id, user_id))
        
        document = cursor.fetchone()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Download from GCS
        file_content = gcs_service.download_file(document['gcs_file_id'], user_id)
        
        from fastapi.responses import Response
        return Response(
            content=file_content,
            media_type=document['mime_type'] or 'application/octet-stream',
            headers={"Content-Disposition": f"attachment; filename={document['title']}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
    finally:
        if connection and connection.is_connected():
            connection.close()

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """Delete a document"""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get document info
        cursor.execute("""
            SELECT gcs_file_id FROM documents 
            WHERE id = %s AND user_id = %s
        """, (document_id, user_id))
        
        document = cursor.fetchone()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete from GCS
        gcs_service.delete_file(document['gcs_file_id'], user_id)
        
        # Delete from database
        cursor.execute("DELETE FROM documents WHERE id = %s AND user_id = %s", (document_id, user_id))
        connection.commit()
        
        return {"success": True, "message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
    finally:
        if connection and connection.is_connected():
            connection.close()