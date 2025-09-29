from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth_service import get_current_user
from services.ai_services import ai_services
from services.gcs_service import gcs_service
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
            try:
                rag_response = await ai_services.query_rag(request.question, request.docId)
            except Exception as e:
                logger.error(f"RAG query failed: {e}")
                rag_response = {
                    "answer": "I apologize, but I'm unable to process your question at the moment. Please try again later.",
                    "sources": [],
                    "confidence": 0.0
                }

            # Fallback: if no vectors matched, try extracting text now and answering directly
            if not rag_response.get("sources") and rag_response.get("confidence", 0.0) == 0.0:
                try:
                    # Get document metadata
                    cursor.execute('''
                        SELECT gcs_file_id, title, mime_type 
                        FROM "documents" 
                        WHERE id = %s AND user_id = %s
                    ''', (request.docId, user_id))
                    doc_row = cursor.fetchone()
                    if doc_row:
                        file_bytes = gcs_service.download_file(doc_row['gcs_file_id'], user_id)
                        extracted_text = ai_services.extract_text_from_file(file_bytes, doc_row['title'] or 'document')
                        if extracted_text and len(extracted_text.strip()) >= 50:
                            # Create embeddings on-the-fly for future queries
                            try:
                                chunks = ai_services.split_text(extracted_text)
                                await ai_services.create_embeddings(chunks, request.docId)
                            except Exception as embed_err:
                                logger.warning(f"On-demand embedding creation failed: {embed_err}")

                            # Answer directly using Gemini constrained to extracted text
                            limited_context = extracted_text[:30000]
                            prompt = f"""
                            Based ONLY on the following extracted text from the user's document, answer the question. 
                            If the text doesn't contain the answer, say so explicitly.

                            Text:\n{limited_context}

                            Question: {request.question}
                            """
                            try:
                                response = ai_services.gemini_model.generate_content(prompt)
                                direct_answer = response.text
                                if direct_answer:
                                    rag_response = {
                                        "answer": direct_answer,
                                        "sources": [],
                                        "confidence": 0.5
                                    }
                            except Exception as gen_err:
                                logger.warning(f"Direct LLM answer failed: {gen_err}")
                except Exception as fb_err:
                    logger.warning(f"Fallback processing failed: {fb_err}")
            
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
    """Get chat history for a document with improved error handling"""
    try:
        # Use userId from query if provided, otherwise use authenticated user_id
        final_user_id = userId if userId else user_id
        
        logger.info(f"Fetching chat history for document {docId} and user {final_user_id}")
        
        with get_db_connection() as connection:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            # First verify the document exists and user has access
            cursor.execute('''
                SELECT id FROM "documents" 
                WHERE id = %s AND user_id = %s
            ''', (docId, final_user_id))
            
            if not cursor.fetchone():
                logger.warning(f"Document {docId} not found for user {final_user_id}")
                return {"messages": [], "error": "Document not found or access denied"}
            
            cursor.execute('''
                SELECT id, role, content, created_at
                FROM "qnas" 
                WHERE document_id = %s AND user_id = %s
                ORDER BY created_at ASC
            ''', (docId, final_user_id))
            
            messages = cursor.fetchall()
            
            logger.info(f"Found {len(messages)} messages for document {docId}")
            
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