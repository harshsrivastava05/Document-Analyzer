from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import google.generativeai as genai
from google.cloud import storage
import google.auth
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

# Initialize Google Cloud Storage
storage_client = storage.Client()
bucket_name = os.getenv("GCS_BUCKET_NAME")

# ----------------- Models -----------------
class DocumentUpload(BaseModel):
    filename: str
    content_type: str
    gcs_blob_name: Optional[str] = None

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
def get_current_user_from_header(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT token and return user_id"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user_from_form(user_id: str):
    """Get user_id from form data (for upload endpoint)"""
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    return user_id

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

# ----------------- Google Cloud Storage -----------------
def upload_to_gcs(file_content: bytes, filename: str, content_type: str):
    """Upload file to Google Cloud Storage."""
    try:
        bucket = storage_client.bucket(bucket_name)
        # Create a unique blob name to avoid conflicts
        blob_name = f"documents/{uuid.uuid4()}_{filename}"
        blob = bucket.blob(blob_name)
        
        # Upload the file
        blob.upload_from_string(file_content, content_type=content_type)
        
        # Make the blob publicly readable (optional - adjust based on your security needs)
        # blob.make_public()
        
        return blob_name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload to GCS: {str(e)}")

def get_gcs_file_url(blob_name: str):
    """Get the public URL for a GCS file."""
    return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"

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
    
    # For Gemini, we need to save the file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
        temp_file.write(file_content)
        temp_file_path = temp_file.name
    
    try:
        file = genai.upload_file(path=temp_file_path, display_name=os.path.basename(filename))

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
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

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

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "DocAnalyzer AI API is running", "status": "healthy"}

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    userId: str = None  # Accept userId from form data
):
    """Handles document upload, analysis, and embedding."""
    temp_file_path = None
    connection = None
    try:
        # Validate user
        user_id = get_current_user_from_form(userId)
        
        # Read file content
        file_content = await file.read()
        
        # Upload to Google Cloud Storage
        blob_name = upload_to_gcs(file_content, file.filename, file.content_type)
        
        # Perform analysis with Gemini
        analysis = await analyze_document_with_gemini(file_content, file.filename)

        # Handle database operations
        connection = get_db_connection()
        cursor = connection.cursor()

        document_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO documents (id, user_id, filename, gcs_blob_name, analysis_data, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            document_id, user_id, file.filename, blob_name,
            json.dumps(analysis), datetime.utcnow()
        ))
        connection.commit()

        # Create embeddings for the RAG pipeline
        text_content = file_content.decode('utf-8', errors='ignore')
        text_chunks = split_text(text_content)
        await create_embeddings(text_chunks, document_id)

        return {
            "document_id": document_id,
            "gcs_blob_name": blob_name,
            "gcs_url": get_gcs_file_url(blob_name),
            "analysis": analysis,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during upload: {str(e)}")
    finally:
        if connection and connection.is_connected():
            connection.close()

@app.post("/ask")
async def chat_with_document(
    chat_request: dict  # Accept as dict to handle both JSON and form data
):
    """Handles chat queries against a specific document."""
    connection = None
    try:
        # Extract data from request
        document_id = chat_request.get("docId")
        message = chat_request.get("question")
        user_id = chat_request.get("userId")
        
        if not all([document_id, message, user_id]):
            raise HTTPException(status_code=400, detail="Missing required fields: docId, question, userId")
        
        rag_response = await query_rag(message, document_id)

        connection = get_db_connection()
        cursor = connection.cursor()
        chat_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO chat_history (id, user_id, document_id, question, answer, sources, confidence, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            chat_id, user_id, document_id,
            message, rag_response["answer"],
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

@app.get("/documents")
async def get_user_documents(userId: str):
    """Retrieves all documents for the specified user."""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, filename, gcs_blob_name, analysis_data, created_at
            FROM documents WHERE user_id = %s ORDER BY created_at DESC
        """, (userId,))
        documents = cursor.fetchall()
        
        # Add GCS URLs and parse analysis data
        for doc in documents:
            if doc['gcs_blob_name']:
                doc['gcs_url'] = get_gcs_file_url(doc['gcs_blob_name'])
            if doc['analysis_data']:
                doc['analysis'] = json.loads(doc['analysis_data'])
                # Extract summary for display
                doc['summary'] = doc['analysis'].get('summary', '')
            doc['title'] = doc['filename']  # Use filename as title
            
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")
    finally:
        if connection and connection.is_connected():
            connection.close()

@app.get("/chat-history")
async def get_chat_history(docId: str, userId: str):
    """Retrieves the chat history for a specific document."""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, question, answer, sources, confidence, created_at
            FROM chat_history WHERE document_id = %s AND user_id = %s
            ORDER BY created_at ASC
        """, (docId, userId))
        chat_history = cursor.fetchall()
        
        # Format chat history for frontend
        messages = []
        for chat in chat_history:
            # Add user message
            messages.append({
                "id": f"{chat['id']}_user",
                "role": "user",
                "content": chat['question'],
                "createdAt": chat['created_at']
            })
            # Add assistant message
            messages.append({
                "id": f"{chat['id']}_assistant",
                "role": "assistant",
                "content": chat['answer'],
                "sources": json.loads(chat['sources']) if chat['sources'] else [],
                "confidence": chat['confidence'],
                "createdAt": chat['created_at']
            })
        
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat history: {str(e)}")
    finally:
        if connection and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)