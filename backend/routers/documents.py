from fastapi import APIRouter, Depends, HTTPException, Query  # type: ignore
from services.auth_service import get_current_user
from services.gcs_service import gcs_service
from database import get_db_connection
from models.schemas import DocumentResponse
from typing import List
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Add this debug route to backend/routers/documents.py

@router.get("/debug/user-documents")
async def debug_user_documents(
    user_id: str = Depends(get_current_user),
    userId: str = Query(None)
):
    """Debug endpoint to investigate user ID mismatch"""
    try:
        # Use userId from query param if provided (for frontend compatibility)
        final_user_id = userId if userId else user_id
        
        logger.info(f"🔍 DEBUG: JWT user_id from token: {user_id}")
        logger.info(f"🔍 DEBUG: Query param userId: {userId}")
        logger.info(f"🔍 DEBUG: Final user_id being used: {final_user_id}")
        
        with get_db_connection() as connection:
            cursor = connection.cursor()
            
            # Get ALL documents in the database for debugging
            cursor.execute('''
                SELECT id, title, gcs_file_id, user_id, created_at
                FROM "documents" 
                ORDER BY created_at DESC
                LIMIT 10
            ''')
            all_documents = cursor.fetchall()
            logger.info(f"🔍 DEBUG: Total documents in database: {len(all_documents)}")
            
            for doc in all_documents:
                logger.info(f"🔍 DEBUG: Document {doc['title']} belongs to user_id: {doc['user_id']}")
            
            # Get documents for current user
            cursor.execute('''
                SELECT id, title, gcs_file_id, mime_type, file_size, summary, created_at, updated_at
                FROM "documents" 
                WHERE user_id = %s 
                ORDER BY created_at DESC
            ''', (final_user_id,))
            
            user_documents = cursor.fetchall()
            logger.info(f"🔍 DEBUG: Documents found for user {final_user_id}: {len(user_documents)}")
            
            # Check if user exists in users table
            cursor.execute('SELECT id, email, name FROM "users" WHERE id = %s', (final_user_id,))
            user_record = cursor.fetchone()
            if user_record:
                logger.info(f"🔍 DEBUG: User found in users table: {user_record['email']}")
            else:
                logger.error(f"🔍 DEBUG: User NOT found in users table with ID: {final_user_id}")
                
                # Check all users
                cursor.execute('SELECT id, email, name FROM "users" ORDER BY created_at DESC LIMIT 5')
                all_users = cursor.fetchall()
                logger.info(f"🔍 DEBUG: Recent users in database:")
                for user in all_users:
                    logger.info(f"🔍 DEBUG: User ID: {user['id']}, Email: {user['email']}")
            
            return {
                "jwt_user_id": user_id,
                "query_user_id": userId,
                "final_user_id": final_user_id,
                "user_documents_count": len(user_documents),
                "user_documents": [
                    {
                        "id": doc["id"],
                        "title": doc["title"],
                        "user_id": final_user_id  # This will show what user_id was used for the query
                    } for doc in user_documents
                ],
                "all_documents_sample": [
                    {
                        "id": doc["id"],
                        "title": doc["title"],
                        "owner_user_id": doc["user_id"]  # This will show the actual user_id in database
                    } for doc in all_documents[:3]  # Just first 3 for reference
                ],
                "user_exists": user_record is not None,
                "user_email": user_record["email"] if user_record else None
            }
        
    except Exception as e:
        logger.error(f"Debug endpoint failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Debug failed: {str(e)}")

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
            cursor = connection.cursor()
            
            cursor.execute('''
                SELECT id, title, gcs_file_id, mime_type, file_size, summary, created_at, updated_at
                FROM "documents" 
                WHERE user_id = %s 
                ORDER BY created_at DESC
            ''', (final_user_id,))
            
            documents = cursor.fetchall()
            
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
                    "created_at": doc["created_at"],
                    "updated_at": doc["updated_at"]
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
            cursor = connection.cursor()
            
            cursor.execute('''
                SELECT gcs_file_id, title, mime_type 
                FROM "documents" 
                WHERE id = %s AND user_id = %s
            ''', (document_id, user_id))
            
            document = cursor.fetchone()
            if not document:
                raise HTTPException(status_code=404, detail="Document not found")
            
            # Download from GCS
            file_content = gcs_service.download_file(document['gcs_file_id'], user_id)
            
            from fastapi.responses import Response  # type: ignore
            return Response(
                content=file_content,
                media_type=document['mime_type'] or 'application/octet-stream',
                headers={"Content-Disposition": f"attachment; filename={document['title']}"}
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
            cursor = connection.cursor()
            
            # Get document info
            cursor.execute('''
                SELECT gcs_file_id FROM "documents" 
                WHERE id = %s AND user_id = %s
            ''', (document_id, user_id))
            
            document = cursor.fetchone()
            if not document:
                raise HTTPException(status_code=404, detail="Document not found")
            
            # Delete from GCS
            gcs_service.delete_file(document['gcs_file_id'], user_id)
            
            # Delete from database (CASCADE will handle qnas)
            cursor.execute('DELETE FROM "documents" WHERE id = %s AND user_id = %s', (document_id, user_id))
            connection.commit()
            
            return {"success": True, "message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")