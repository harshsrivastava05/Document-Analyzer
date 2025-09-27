# backend/routers/upload.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from services.auth_service import get_current_user
from services.gcs_service import gcs_service
from services.ai_services import ai_services
from database import get_db_connection
from models.schemas import UploadResponse, DocumentResponse
from psycopg2.extras import RealDictCursor
import uuid
import json
from datetime import datetime
import logging
from typing import Optional
import traceback
import psycopg2
import time

router = APIRouter()
logger = logging.getLogger(__name__)

def generate_cuid():
    """Generate a CUID-like ID to match Prisma"""
    return str(uuid.uuid4()).replace('-', '')[:25]

def safe_db_operation(operation_func, *args, max_retries=3, **kwargs):
    """Safely execute database operations with retry logic"""
    for attempt in range(max_retries):
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor(cursor_factory=RealDictCursor)
                result = operation_func(cursor, *args, **kwargs)
                connection.commit()
                return result
        except (psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.Error) as db_error:
            logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}): {db_error}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"Database operation failed after {max_retries} attempts")
                raise HTTPException(
                    status_code=503, 
                    detail=f"Database temporarily unavailable: {str(db_error)}"
                )
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def create_or_update_document(cursor, document_id, user_id, filename, file_id, gcs_path, content_type, file_size):
    """Database operation to create or update document"""
    try:
        # Check if document exists
        cursor.execute('''
            SELECT id FROM "documents" WHERE id = %s AND user_id = %s
        ''', (document_id, user_id))
        
        existing_doc = cursor.fetchone()
        
        if existing_doc:
            # Update existing document
            cursor.execute('''
                UPDATE "documents" 
                SET gcs_file_id = %s, gcs_file_path = %s, mime_type = %s, 
                    file_size = %s, summary = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s
                RETURNING *
            ''', (
                file_id, gcs_path, content_type, 
                file_size, 'Processing with AI...', 
                document_id, user_id
            ))
        else:
            # Create new document
            cursor.execute('''
                INSERT INTO "documents" 
                (id, user_id, title, gcs_file_id, gcs_file_path, mime_type, file_size, summary, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING *
            ''', (
                document_id, user_id, filename, file_id, gcs_path,
                content_type, file_size, 'Processing with AI...'
            ))
        
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error in create_or_update_document: {e}")
        raise

def update_document_summary(cursor, document_id, user_id, summary):
    """Database operation to update document summary"""
    cursor.execute('''
        UPDATE "documents" 
        SET summary = %s, updated_at = NOW()
        WHERE id = %s AND user_id = %s
    ''', (summary, document_id, user_id))
    return cursor.rowcount > 0

async def process_document_background(
    file_content: bytes, 
    filename: str, 
    document_id: str, 
    user_id: str,
    gcs_file_id: str
):
    """Background task to process document with AI services"""
    try:
        logger.info(f"🤖 Starting background processing for document {document_id}")
        
        # 1. Analyze document with Gemini AI
        analysis_result = await ai_services.analyze_document(file_content, filename)
        
        # 2. Extract text and create embeddings
        try:
            text_content = file_content.decode('utf-8', errors='ignore')
        except:
            text_content = analysis_result.get('summary', '')
        
        if text_content:
            text_chunks = ai_services.split_text(text_content)
            await ai_services.create_embeddings(text_chunks, document_id)
        
        # 3. Update document with analysis results
        summary = analysis_result.get('summary', 'Analysis completed')
        safe_db_operation(update_document_summary, document_id, user_id, summary)
        
        logger.info(f"✅ Background processing completed for document {document_id}")
        
    except Exception as e:
        logger.error(f"❌ Background processing failed for document {document_id}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Update document with error status
        try:
            error_summary = f'Processing failed: {str(e)[:200]}'
            safe_db_operation(update_document_summary, document_id, user_id, error_summary)
        except Exception as db_error:
            logger.error(f"Failed to update document error status: {db_error}")

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    documentId: Optional[str] = Form(None)
):
    """Upload and process document with JWT authentication"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain'
        ]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only PDF, DOC, DOCX, and TXT files are allowed."
            )
        
        # Validate file size (10MB max)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
        
        logger.info(f"📄 Processing upload: {file.filename} for user {user_id}")
        
        # Upload to Google Cloud Storage first
        try:
            file_id, gcs_path = gcs_service.upload_file(
                file_content, 
                file.filename, 
                file.content_type or "application/octet-stream",
                user_id
            )
            logger.info(f"☁️ File uploaded to GCS: {gcs_path}")
        except Exception as gcs_error:
            logger.error(f"❌ GCS upload failed: {gcs_error}")
            raise HTTPException(status_code=500, detail=f"File storage failed: {str(gcs_error)}")
        
        # Generate document ID if not provided
        if not documentId:
            documentId = generate_cuid()
        
        # Save to database using safe operation
        try:
            document = safe_db_operation(
                create_or_update_document,
                documentId, user_id, file.filename, file_id, gcs_path,
                file.content_type, len(file_content)
            )
            logger.info(f"✅ Document saved to database: {documentId}")
        except HTTPException:
            raise
        except Exception as db_error:
            logger.error(f"❌ Database save failed: {db_error}")
            raise HTTPException(
                status_code=503, 
                detail=f"File uploaded but database save failed: {str(db_error)}"
            )
        
        # Add background task for AI processing
        try:
            background_tasks.add_task(
                process_document_background,
                file_content=file_content,
                filename=file.filename,
                document_id=documentId,
                user_id=user_id,
                gcs_file_id=file_id
            )
            logger.info(f"📋 Background task queued for document {documentId}")
        except Exception as task_error:
            logger.warning(f"⚠️ Failed to queue background task: {task_error}")
        
        logger.info(f"✅ Document uploaded and queued for processing: {documentId}")
        
        # Create response
        document_response = DocumentResponse(
            id=document['id'],
            title=document['title'],
            gcs_file_id=document['gcs_file_id'],
            mime_type=document['mime_type'],
            file_size=document['file_size'],
            summary=document['summary'],
            created_at=document['created_at'],
            updated_at=document['updated_at']
        )
        
        return UploadResponse(
            success=True,
            document=document_response,
            message="Document uploaded and processing with AI..."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/upload-direct", response_model=UploadResponse)
async def upload_document_direct(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    userId: str = Form(...),
    documentId: Optional[str] = Form(None)
):
    """Upload document with userId from form data (alternative for frontend integration)"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain'
        ]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only PDF, DOC, DOCX, and TXT files are allowed."
            )
        
        # Validate file size (10MB max)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
        
        logger.info(f"📄 Processing direct upload: {file.filename} for user {userId}")
        
        # Upload to Google Cloud Storage first
        try:
            file_id, gcs_path = gcs_service.upload_file(
                file_content, 
                file.filename, 
                file.content_type or "application/octet-stream",
                userId
            )
            logger.info(f"☁️ File uploaded to GCS: {gcs_path}")
        except Exception as gcs_error:
            logger.error(f"❌ GCS upload failed: {gcs_error}")
            raise HTTPException(status_code=500, detail=f"File storage failed: {str(gcs_error)}")
        
        # Generate document ID if not provided
        if not documentId:
            documentId = generate_cuid()
        
        # Save to database using safe operation
        try:
            document = safe_db_operation(
                create_or_update_document,
                documentId, userId, file.filename, file_id, gcs_path,
                file.content_type, len(file_content)
            )
            logger.info(f"✅ Document saved to database: {documentId}")
        except HTTPException:
            raise
        except Exception as db_error:
            logger.error(f"❌ Database save failed: {db_error}")
            raise HTTPException(
                status_code=503, 
                detail=f"File uploaded but database save failed: {str(db_error)}"
            )
        
        # Add background task for AI processing
        try:
            background_tasks.add_task(
                process_document_background,
                file_content=file_content,
                filename=file.filename,
                document_id=documentId,
                user_id=userId,
                gcs_file_id=file_id
            )
            logger.info(f"📋 Background task queued for document {documentId}")
        except Exception as task_error:
            logger.warning(f"⚠️ Failed to queue background task: {task_error}")
        
        logger.info(f"✅ Document uploaded and queued for processing: {documentId}")
        
        # Create response
        document_response = DocumentResponse(
            id=document['id'],
            title=document['title'],
            gcs_file_id=document['gcs_file_id'],
            mime_type=document['mime_type'],
            file_size=document['file_size'],
            summary=document['summary'],
            created_at=document['created_at'],
            updated_at=document['updated_at']
        )
        
        return UploadResponse(
            success=True,
            document=document_response,
            message="Document uploaded and processing with AI..."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

def get_document_status(cursor, document_id, user_id):
    """Database operation to get document status"""
    cursor.execute('''
        SELECT id, title, summary, created_at, updated_at
        FROM "documents" 
        WHERE id = %s AND user_id = %s
    ''', (document_id, user_id))
    
    return cursor.fetchone()

@router.get("/upload/status/{document_id}")
async def get_upload_status(
    document_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get the processing status of an uploaded document"""
    try:
        document = safe_db_operation(get_document_status, document_id, current_user)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Determine processing status based on summary content
        summary = document['summary'] or ''
        if 'Processing' in summary or 'processing' in summary:
            status = 'processing'
        elif 'failed' in summary.lower() or 'error' in summary.lower():
            status = 'failed'
        else:
            status = 'completed'
        
        return {
            "document_id": document['id'],
            "title": document['title'],
            "status": status,
            "summary": summary,
            "created_at": document['created_at'].isoformat() if document['created_at'] else None,
            "updated_at": document['updated_at'].isoformat() if document['updated_at'] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get upload status: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to get document status"
        )