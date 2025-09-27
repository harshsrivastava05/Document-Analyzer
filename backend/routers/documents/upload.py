from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from services.auth.token_service import get_current_user
from services.storage.gcs_service import gcs_service
from services.ai_services import ai_services
from db.connection import get_db_connection
from psycopg2.extras import RealDictCursor
import uuid, time, psycopg2, traceback
from datetime import datetime
import logging
from typing import Optional
from typing import List, Dict, Any, Optional

router = APIRouter()
logger = logging.getLogger(__name__)


def generate_cuid():
    return str(uuid.uuid4()).replace('-', '')[:25]


def verify_user_exists(cursor, user_id):
    cursor.execute('SELECT id FROM "users" WHERE id=%s', (user_id,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO "users" (id, created_at, updated_at) VALUES (%s, NOW(), NOW()) ON CONFLICT (id) DO NOTHING', (user_id,))


def create_or_update_document(cursor, document_id, user_id, filename, file_id, gcs_path, content_type, file_size):
    verify_user_exists(cursor, user_id)
    cursor.execute('SELECT id FROM "documents" WHERE id=%s AND user_id=%s', (document_id, user_id))
    if cursor.fetchone():
        cursor.execute('''
            UPDATE "documents" SET gcs_file_id=%s, gcs_file_path=%s, mime_type=%s, file_size=%s, summary=%s, updated_at=NOW()
            WHERE id=%s AND user_id=%s RETURNING *
        ''', (file_id, gcs_path, content_type, file_size, 'Processing with Gemini...', document_id, user_id))
    else:
        cursor.execute('''
            INSERT INTO "documents" (id, user_id, title, gcs_file_id, gcs_file_path, mime_type, file_size, summary, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW()) RETURNING *
        ''', (document_id, user_id, filename, file_id, gcs_path, content_type, file_size, 'Processing with Gemini...'))
    return cursor.fetchone()


def update_document_summary(cursor, document_id, user_id, summary):
    cursor.execute('UPDATE "documents" SET summary=%s, updated_at=NOW() WHERE id=%s AND user_id=%s RETURNING id, title, summary, updated_at', (summary, document_id, user_id))
    return cursor.fetchone()


async def process_document_background(file_content: bytes, filename: str, document_id: str, user_id: str):
    try:
        analysis = await ai_services.analyze_document(file_content, filename)
        text = ai_services.extract_text_from_file(file_content, filename)
        if text.strip():
            chunks = ai_services.split_text(text)
            await ai_services.create_embeddings(chunks, document_id)
        summary = analysis.get('summary', 'Analysis completed')
        with get_db_connection() as connection:
            cur = connection.cursor()
            update_document_summary(cur, document_id, user_id, summary)
            connection.commit()
    except Exception as e:
        logger.error(f"Background processing failed: {e}\n{traceback.format_exc()}")
        with get_db_connection() as connection:
            cur = connection.cursor()
            update_document_summary(cur, document_id, user_id, f"AI processing failed: {str(e)[:200]}")
            connection.commit()


@router.post("/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...), user_id: str = Depends(get_current_user), documentId: Optional[str] = Form(None)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    allowed = {'application/pdf','application/msword','application/vnd.openxmlformats-officedocument.wordprocessingml.document','text/plain'}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Invalid file type")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    file_id, gcs_path = gcs_service.upload_file(content, file.filename, file.content_type or 'application/octet-stream', user_id)
    document_id = documentId or generate_cuid()

    with get_db_connection() as connection:
        cur = connection.cursor(cursor_factory=RealDictCursor)
        doc = create_or_update_document(cur, document_id, user_id, file.filename, file_id, gcs_path, file.content_type, len(content))
        connection.commit()

    background_tasks.add_task(process_document_background, file_content=content, filename=file.filename, document_id=document_id, user_id=user_id)

    return {"success": True, "document": doc, "message": "Document uploaded. Analysis in progress."}