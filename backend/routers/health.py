from fastapi import APIRouter
from datetime import datetime
from models.schemas import HealthCheck

router = APIRouter()

@router.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.utcnow(),
        services={
            "database": "connected",
            "gemini": "initialized",
            "pinecone": "connected",
            "cohere": "connected",
            "gcs": "connected"
        }
    )