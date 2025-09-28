# backend/routers/upload.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks #type:ignore
from services.auth_service import get_current_user
from services.gcs_service import gcs_service
from services.ai_services import ai_services
from database import get_db_connection
from models.schemas import UploadResponse, DocumentResponse
from psycopg2.extras import RealDictCursor #type:ignore
import uuid
import json
from datetime import datetime
import logging
from typing import Optional

router = APIRouter()
logger = logging.getLogger(__name__)

def generate_cuid():
    """Generate a CUID-like ID to match Prisma"""
    return str(uuid.uuid4()).replace('-', '')[:25]

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
        try:
            analysis_result = await ai_services.analyze_document(file_content, filename)
            logger.info(f"📊 AI analysis completed for document {document_id}")
        except Exception as e:
            logger.error(f"❌ AI analysis failed for document {document_id}: {e}")
            analysis_result = {
                "summary": "Document uploaded successfully but AI analysis is currently unavailable.",
                "key_topics": [],
                "entities": [],
                "sentiment": "neutral",
                "confidence": 0.0
            }
        
        # 2. Extract text and create embeddings for RAG
        try:
            # For PDF/DOC files, try to decode as text, otherwise use summary
            try:
                text_content = file_content.decode('utf-8', errors='ignore')
                # Clean up the text content
                text_content = text_content.strip()
                if len(text_content) < 50:  # Too short, likely not meaningful text
                    text_content = analysis_result.get('summary', '')
            except:
                text_content = analysis_result.get('summary', '')
            
            if text_content and len(text_content.strip()) > 50:
                text_chunks = ai_services.split_text(text_content)
                await ai_services.create_embeddings(text_chunks, document_id)
                logger.info(f"🔍 Created embeddings for {len(text_chunks)} text chunks")
            else:
                logger.warning(f"⚠️ No meaningful text content found for embeddings in document {document_id}")
                
        except Exception as e:
            logger.error(f"❌ Embedding creation failed for document {document_id}: {e}")
        
        # 3. Update document in database with analysis results
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor(cursor_factory=RealDictCursor)
                
                cursor.execute('''
                    UPDATE "documents" 
                    SET summary = %s, updated_at = NOW()
                    WHERE id = %s AND user_id = %s
                ''', (analysis_result.get('summary', 'Analysis completed'), document_id, user_id))
                
                connection.commit()
                logger.info(f"📝 Document {document_id} updated with analysis results")
        except Exception as e:
            logger.error(f"❌ Failed to update document {document_id}: {e}")
        
        logger.info(f"✅ Background processing completed for document {document_id}")
        
    except Exception as e:
        logger.error(f"❌ Background processing failed for document {document_id}: {e}")
        
        # Update document with error status
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor(cursor_factory=RealDictCursor)
                cursor.execute('''
                    UPDATE "documents" 
                    SET summary = %s, updated_at = NOW()
                    WHERE id = %s AND user_id = %s
                ''', (f'Processing failed: {str(e)[:200]}', document_id, user_id))
                connection.commit()
        except Exception as db_error:
            logger.error(f"Failed to update document error status: {db_error}")

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    documentId: Optional[str] = Form(None)  # Optional, for frontend-created documents
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
        
        # Upload to Google Cloud Storage
        file_id, gcs_path = gcs_service.upload_file(
            file_content, 
            file.filename, 
            file.content_type or "application/octet-stream",
            user_id
        )
        
        logger.info(f"☁️ File uploaded to GCS: {gcs_path}")
        
        # Generate document ID if not provided
        if not documentId:
            documentId = generate_cuid()
        
        # Save to database
        with get_db_connection() as connection:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            # Check if document already exists (for frontend-created documents)
            cursor.execute('''
                SELECT id FROM "documents" WHERE id = %s AND user_id = %s
            ''', (documentId, user_id))
            
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
                    file_id, gcs_path, file.content_type, 
                    len(file_content), 'Processing with AI...', 
                    documentId, user_id
                ))
            else:
                # Create new document
                cursor.execute('''
                    INSERT INTO "documents" 
                    (id, user_id, title, gcs_file_id, gcs_file_path, mime_type, file_size, summary, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING *
                ''', (
                    documentId, user_id, file.filename, file_id, gcs_path,
                    file.content_type, len(file_content), 'Processing with AI...'
                ))
            
            document = cursor.fetchone()
            connection.commit()
        
        # Add background task for AI processing
        background_tasks.add_task(
            process_document_background,
            file_content=file_content,
            filename=file.filename,
            document_id=documentId,
            user_id=user_id,
            gcs_file_id=file_id
        )
        
        logger.info(f"✅ Document uploaded and queued for processing: {documentId}")
        
        # Create response with redirect information
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
            message="Document uploaded successfully and is being processed with AI",
            redirect={
                "url": f"/chat/{documentId}",
                "delay": 2000  # 2 second delay for user to see success message
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/upload-direct", response_model=UploadResponse)
async def upload_document_direct(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    userId: str = Form(...),  # Accept userId directly from form
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
        
        # Upload to Google Cloud Storage
        file_id, gcs_path = gcs_service.upload_file(
            file_content, 
            file.filename, 
            file.content_type or "application/octet-stream",
            userId
        )
        
        logger.info(f"☁️ File uploaded to GCS: {gcs_path}")
        
        # Generate document ID if not provided
        if not documentId:
            documentId = generate_cuid()
        
        # Save to database
        with get_db_connection() as connection:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            # Check if document already exists (for frontend-created documents)
            cursor.execute('''
                SELECT id FROM "documents" WHERE id = %s AND user_id = %s
            ''', (documentId, userId))
            
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
                    file_id, gcs_path, file.content_type, 
                    len(file_content), 'Processing with AI...', 
                    documentId, userId
                ))
            else:
                # Create new document
                cursor.execute('''
                    INSERT INTO "documents" 
                    (id, user_id, title, gcs_file_id, gcs_file_path, mime_type, file_size, summary, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING *
                ''', (
                    documentId, userId, file.filename, file_id, gcs_path,
                    file.content_type, len(file_content), 'Processing with AI...'
                ))
            
            document = cursor.fetchone()
            connection.commit()
        
        # Add background task for AI processing
        background_tasks.add_task(
            process_document_background,
            file_content=file_content,
            filename=file.filename,
            document_id=documentId,
            user_id=userId,
            gcs_file_id=file_id
        )
        
        logger.info(f"✅ Document uploaded and queued for processing: {documentId}")
        
        # Create response with redirect information
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
            message="Document uploaded successfully and is being processed with AI",
            redirect={
                "url": f"/chat/{documentId}",
                "delay": 2000  # 2 second delay for user to see success message
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/upload/status/{document_id}")
async def get_upload_status(
    document_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get the processing status of an uploaded document"""
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute('''
                SELECT id, title, summary, created_at, updated_at
                FROM "documents" 
                WHERE id = %s AND user_id = %s
            ''', (document_id, current_user))
            
            document = cursor.fetchone()
            
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
                "updated_at": document['updated_at'].isoformat() if document['updated_at'] else None,
                "chat_ready": status == 'completed',  # Indicates if ready for chat
                "redirect_url": f"/chat/{document['id']}" if status == 'completed' else None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get upload status: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to get document status"
        )