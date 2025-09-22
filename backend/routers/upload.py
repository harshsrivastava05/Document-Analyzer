from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from services.auth_service import get_current_user
from services.gcs_service import gcs_service
from services.ai_services import ai_services
from database import get_db_connection
from models.schemas import UploadResponse, DocumentResponse
import uuid
import json
from datetime import datetime

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """Upload and process document"""
    connection = None
    try:
        # Validate file
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
        
        # Upload to Google Cloud Storage
        file_id, gcs_path = gcs_service.upload_file(
            file_content, 
            file.filename or "document", 
            file.content_type or "application/octet-stream",
            user_id
        )
        
        # Analyze document with AI
        analysis = await ai_services.analyze_document(file_content, file.filename or "document")
        
        # Save to database
        connection = get_db_connection()
        cursor = connection.cursor()
        document_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO documents 
            (id, user_id, title, gcs_file_id, gcs_file_path, mime_type, file_size, summary, analysis_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            document_id, user_id, file.filename or "Untitled",
            file_id, gcs_path, file.content_type, len(file_content),
            analysis.get('summary', ''), json.dumps(analysis)
        ))
        
        connection.commit()
        
        # Create embeddings for RAG
        text_content = file_content.decode('utf-8', errors='ignore')
        text_chunks = ai_services.split_text(text_content)
        await ai_services.create_embeddings(text_chunks, document_id)
        
        document_response = DocumentResponse(
            id=document_id,
            title=file.filename or "Untitled",
            gcs_file_id=file_id,
            mime_type=file.content_type,
            file_size=len(file_content),
            summary=analysis.get('summary', ''),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return UploadResponse(
            success=True,
            document=document_response,
            message="Document uploaded and processed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        if connection and connection.is_connected():
            connection.close()

@router.post("/process-document")
async def process_document_webhook(
    documentId: str = Form(...),
    userId: str = Form(...),
    gcsFileId: str = Form(...),
    fileName: str = Form(...),
    mimeType: str = Form(...)
):
    """Process document from frontend GCS upload (webhook-style endpoint)"""
    connection = None
    try:
        # Download file from GCS
        file_content = gcs_service.download_file(gcsFileId, userId)
        
        # Analyze document
        analysis = await ai_services.analyze_document(file_content, fileName)
        
        # Update database with analysis
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            UPDATE documents 
            SET summary = %s, analysis_data = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
        """, (
            analysis.get('summary', ''),
            json.dumps(analysis),
            documentId,
            userId
        ))
        
        connection.commit()
        
        # Create embeddings for RAG
        text_content = file_content.decode('utf-8', errors='ignore')
        text_chunks = ai_services.split_text(text_content)
        await ai_services.create_embeddings(text_chunks, documentId)
        
        return {"success": True, "message": "Document processed successfully"}
        
    except Exception as e:
        print(f"❌ Document processing failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        if connection and connection.is_connected():
            connection.close()
