from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth_service import get_current_user
from services.ai_services import ai_services
from database import get_db_connection
from models.schemas import ChatRequest, ChatResponse, ChatMessage
from typing import List
import uuid
import json
from datetime import datetime

router = APIRouter()

@router.post("/ask")
async def ask_question(
    request: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    """Ask a question about a document"""
    connection = None
    try:
        # Verify user has access to document
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT id FROM documents 
            WHERE id = %s AND user_id = %s
        """, (request.docId, user_id))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get RAG response
        rag_response = await ai_services.query_rag(request.question, request.docId)
        
        # Save user message
        user_chat_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO chat_history (id, user_id, document_id, role, content, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_chat_id, user_id, request.docId, 'user', request.question, datetime.utcnow()))
        
        # Save assistant response
        assistant_chat_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO chat_history (id, user_id, document_id, role, content, sources, confidence, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            assistant_chat_id, user_id, request.docId, 'assistant',
            rag_response["answer"], json.dumps(rag_response["sources"]),
            rag_response["confidence"], datetime.utcnow()
        ))
        
        connection.commit()
        
        return {
            "id": assistant_chat_id,
            "role": "assistant",
            "content": rag_response["answer"],
            "sources": rag_response["sources"],
            "confidence": rag_response["confidence"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Question processing failed: {str(e)}")
    finally:
        if connection and connection.is_connected():
            connection.close()

@router.get("/chat-history")
async def get_chat_history(
    docId: str = Query(...),
    userId: str = Query(...),
    user_id: str = Depends(get_current_user)
):
    """Get chat history for a document"""
    connection = None
    try:
        # Use userId from query if provided, otherwise use authenticated user_id
        final_user_id = userId if userId else user_id
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, role, content, sources, confidence, created_at
            FROM chat_history 
            WHERE document_id = %s AND user_id = %s
            ORDER BY created_at ASC
        """, (docId, final_user_id))
        
        messages = cursor.fetchall()
        
        # Parse sources JSON for each message
        for message in messages:
            if message.get('sources'):
                try:
                    message['sources'] = json.loads(message['sources'])
                except (json.JSONDecodeError, TypeError):
                    message['sources'] = []
            else:
                message['sources'] = []
        
        return {"messages": messages}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat history: {str(e)}")
    finally:
        if connection and connection.is_connected():
            connection.close()