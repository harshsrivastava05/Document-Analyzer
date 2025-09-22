from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class DocumentUpload(BaseModel):
    title: str
    mime_type: str
    file_size: int
    gcs_file_id: Optional[str] = None

class ChatMessage(BaseModel):
    document_id: str = Field(..., description="Document ID to chat about")
    message: str = Field(..., min_length=1, description="User message")
    user_id: str = Field(..., description="User ID")

class ChatRequest(BaseModel):
    docId: str = Field(..., description="Document ID")
    question: str = Field(..., min_length=1, description="User question")

class ChatResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: List[int] = []
    confidence: float = 0.0
    created_at: datetime

class DocumentResponse(BaseModel):
    id: str
    title: str
    gcs_file_id: str
    mime_type: Optional[str]
    file_size: Optional[int]
    summary: Optional[str]
    created_at: datetime
    updated_at: datetime

class DocumentAnalysis(BaseModel):
    summary: str
    key_topics: List[str]
    entities: List[str]
    sentiment: str
    confidence: float

class UploadResponse(BaseModel):
    success: bool
    document: DocumentResponse
    message: str

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    services: dict