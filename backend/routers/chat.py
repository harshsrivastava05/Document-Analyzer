from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth_service import get_current_user
from services.ai_services import ai_services
from database import get_db_connection
from models.schemas import ChatRequest, ChatResponse, ChatMessage
from psycopg2.extras import RealDictCursor
from typing import List
import uuid
import json
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/ask")
async def ask_question(
    request: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    """Ask a question about a document"""
    try:
        # Verify user has access to document
        with get_db_connection() as connection:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute('''
                SELECT id FROM "documents" 
                WHERE id = %s AND user_id = %s
            ''', (request.docId, user_id))
            
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Document not found")
            
            # Get RAG response
            rag_response = await ai_services.query_rag(request.question, request.docId)
            
            # Save user message
            user_chat_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO "qnas" (id, user_id, document_id, role, content, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (user_chat_id, user_id, request.docId, 'user', request.question, datetime.utcnow()))
            
            # Save assistant response
            assistant_chat_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO "qnas" (id, user_id, document_id, role, content, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                assistant_chat_id, user_id, request.docId, 'assistant',
                rag_response["answer"], datetime.utcnow()
            ))
            
            connection.commit()
            
            return {
                "id": assistant_chat_id,
                "role": "assistant",
                "content": rag_response["answer"],
                "sources": rag_response["sources"],
                "confidence": rag_response["confidence"],
                "created_at": datetime.utcnow()
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Question processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Question processing failed: {str(e)}")

@router.get("/chat-history")
async def get_chat_history(
    docId: str = Query(...),
    userId: str = Query(None),
    user_id: str = Depends(get_current_user)
):
    """Get chat history for a document"""
    try:
        # Use userId from query if provided, otherwise use authenticated user_id
        final_user_id = userId if userId else user_id
        
        with get_db_connection() as connection:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute('''
                SELECT id, role, content, created_at
                FROM "qnas" 
                WHERE document_id = %s AND user_id = %s
                ORDER BY created_at ASC
            ''', (docId, final_user_id))
            
            messages = cursor.fetchall()
            
            # Format messages for response
            formatted_messages = []
            for message in messages:
                formatted_messages.append({
                    "id": message["id"],
                    "role": message["role"],
                    "content": message["content"],
                    "sources": [],  # Sources not stored separately in simplified schema
                    "confidence": 0.0,  # Confidence not stored separately in simplified schema
                    "created_at": message["created_at"]
                })
            
            return {"messages": formatted_messages}
        
    except Exception as e:
        logger.error(f"Failed to fetch chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat history: {str(e)}")