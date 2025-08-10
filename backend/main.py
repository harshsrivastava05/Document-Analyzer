from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pinecone import Pinecone
import cohere
import mysql.connector
from mysql.connector import Error
import os
import tempfile # For secure file handling
from typing import List, Optional
import json
import uuid
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="DocAnalyzer AI API",
    description="Advanced AI document processing with RAG pipeline",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust for your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Initialize AI services
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
co = cohere.Client(os.getenv("COHERE_API_KEY"))

# ----------------- Models -----------------
class DocumentUpload(BaseModel):
    filename: str
    content_type: str
    google_drive_id: Optional[str] = None

class ChatMessage(BaseModel):
    document_id: str
    message: str
    user_id: str

class DocumentAnalysis(BaseModel):
    document_id: str
    summary: str
    key_topics: List[str]
    entities: List[str]
    sentiment: str
    confidence: float

# ----------------- Auth -----------------
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT token and return user_id"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ----------------- Database -----------------
def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE")
        )
        return connection
    except Error as e:
        # This will be caught by the endpoint's error handling
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# ----------------- Google Drive -----------------
def get_drive_service(credentials):
    """Builds the Google Drive service object."""
    return build('drive', 'v3', credentials=credentials)

def upload_to_drive(file_path, filename, folder_id):
    """Upload file to Google Drive using a Service Account."""
    credentials = Credentials.from_service_account_file(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        scopes=['https://www.googleapis.com/auth/drive']
    )
    service = get_drive_service(credentials)

    file_metadata = {'name': filename, 'parents': [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    return file.get('id')

# ----------------- Text splitting -----------------
def split_text(text, max_chunk_size=1000):
    """Basic text splitter by words."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0
    for word in words:
        if current_size + len(word) + 1 > max_chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_size = len(word)
        else:
            current_chunk.append(word)
            current_size += len(word) + 1
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

# ----------------- Gemini AI -----------------
async def analyze_document_with_gemini(file_content, filename):
    """Analyze document using Gemini AI."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    file = genai.upload_file(path=filename, display_name=os.path.basename(filename))

    prompt = """
    Analyze this document and provide:
    1. A comprehensive summary (2-3 paragraphs)
    2. Key topics (5-8 main topics)
    3. Important entities (people, places, organizations, dates)
    4. Overall sentiment (positive, negative, neutral)
    5. Confidence score for the analysis (a float between 0 and 1)

    Format the response as a single, valid JSON object with the following structure:
    {
        "summary": "...",
        "key_topics": ["topic1", "topic2", ...],
        "entities": ["entity1", "entity2", ...],
        "sentiment": "positive/negative/neutral",
        "confidence": 0.95
    }
    """
    response = model.generate_content([file, prompt])
    # Clean up the response to ensure it's valid JSON
    cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
    result = json.loads(cleaned_text)
    return result

# ----------------- RAG Pipeline -----------------
async def create_embeddings(text_chunks, document_id):
    """Create embeddings using Cohere and store in Pinecone."""
    embeddings = co.embed(
        texts=text_chunks,
        model="embed-multilingual-v3.0",
        input_type="search_document"
    ).embeddings

    index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

    vectors = []
    for i, (chunk, embedding) in enumerate(zip(text_chunks, embeddings)):
        vector_id = f"{document_id}_{i}"
        vectors.append({
            "id": vector_id,
            "values": embedding,
            "metadata": {
                "document_id": document_id,
                "chunk_index": i,
                "text": chunk
            }
        })
    index.upsert(vectors=vectors)
    return True

async def query_rag(question, document_id, k=5):
    """Query RAG pipeline for document-specific answers."""
    query_embedding = co.embed(
        texts=[question],
        model="embed-multilingual-v3.0",
        input_type="search_query"
    ).embeddings[0]

    index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
    results = index.query(
        vector=query_embedding,
        filter={"document_id": {"$eq": document_id}},
        top_k=k,
        include_metadata=True
    )

    if not results["matches"]:
        return {"answer": "I could not find relevant information in the document to answer your question.", "sources": [], "confidence": 0.0}

    relevant_chunks = [match["metadata"]["text"] for match in results["matches"]]
    context = "\n\n".join(relevant_chunks)
    prompt = f"""
    Based ONLY on the following context from the document, answer the question.
    Do not use any outside knowledge. If the context doesn't contain the answer, state that clearly.

    Context: {context}

    Question: {question}
    """

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)

    return {
        "answer": response.text,
        "sources": [match["metadata"]["chunk_index"] for match in results["matches"]],
        "confidence": max([match["score"] for match in results["matches"]]) if results["matches"] else 0
    }

# ----------------- API Routes -----------------
@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """Handles document upload, analysis, and embedding."""
    temp_file_path = None
    connection = None
    try:
        # Use a secure temporary file to avoid conflicts and ensure cleanup
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            file_content = await file.read()
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        # Perform all file-based operations
        drive_file_id = upload_to_drive(temp_file_path, file.filename, os.getenv("GOOGLE_DRIVE_FOLDER_ID"))
        analysis = await analyze_document_with_gemini(file_content, temp_file_path)

        # Handle database operations
        connection = get_db_connection()
        cursor = connection.cursor()

        document_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO documents (id, user_id, filename, google_drive_id, analysis_data, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            document_id, user_id, file.filename, drive_file_id,
            json.dumps(analysis), datetime.utcnow()
        ))
        connection.commit()

        # Create embeddings for the RAG pipeline
        text_chunks = split_text(file_content.decode(errors="ignore"))
        await create_embeddings(text_chunks, document_id)

        return {
            "document_id": document_id,
            "drive_file_id": drive_file_id,
            "analysis": analysis,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during upload: {str(e)}")
    finally:
        # Ensure resources are always cleaned up
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if connection and connection.is_connected():
            connection.close()

@app.post("/api/chat")
async def chat_with_document(
    chat_request: ChatMessage,
    user_id: str = Depends(get_current_user)
):
    """Handles chat queries against a specific document."""
    connection = None
    try:
        rag_response = await query_rag(chat_request.message, chat_request.document_id)

        connection = get_db_connection()
        cursor = connection.cursor()
        chat_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO chat_history (id, user_id, document_id, question, answer, sources, confidence, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            chat_id, user_id, chat_request.document_id,
            chat_request.message, rag_response["answer"],
            json.dumps(rag_response["sources"]), rag_response["confidence"],
            datetime.utcnow()
        ))
        connection.commit()

        return {
            "chat_id": chat_id,
            "answer": rag_response["answer"],
            "sources": rag_response["sources"],
            "confidence": rag_response["confidence"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during chat: {str(e)}")
    finally:
        if connection and connection.is_connected():
            connection.close()

@app.get("/api/documents")
async def get_user_documents(user_id: str = Depends(get_current_user)):
    """Retrieves all documents for the current user."""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, filename, google_drive_id, analysis_data, created_at
            FROM documents WHERE user_id = %s ORDER BY created_at DESC
        """, (user_id,))
        documents = cursor.fetchall()
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")
    finally:
        if connection and connection.is_connected():
            connection.close()

@app.get("/api/chat-history/{document_id}")
async def get_chat_history(document_id: str, user_id: str = Depends(get_current_user)):
    """Retrieves the chat history for a specific document."""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, question, answer, sources, confidence, created_at
            FROM chat_history WHERE document_id = %s AND user_id = %s
            ORDER BY created_at ASC
        """, (document_id, user_id))
        chat_history = cursor.fetchall()
        return {"chat_history": chat_history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat history: {str(e)}")
    finally:
        if connection and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)