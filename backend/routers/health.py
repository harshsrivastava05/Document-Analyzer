# backend/routers/health.py
from fastapi import APIRouter # type: ignore
from database import test_db_connection, get_db_stats
from services.gcs_service import gcs_service
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db_healthy = test_db_connection()
        
        # Test GCS connection (if configured)
        gcs_healthy = True
        try:
            if os.getenv("GCS_PROJECT_ID") and os.getenv("GCS_BUCKET_NAME"):
                # This will initialize and test GCS connection
                gcs_service._initialize_client()
        except Exception as e:
            logger.warning(f"GCS health check failed: {e}")
            gcs_healthy = False
        
        # Get basic stats
        stats = get_db_stats() if db_healthy else {}
        
        health_status = {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "gcs": "connected" if gcs_healthy else "disconnected",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "stats": stats
        }
        
        status_code = 200 if db_healthy else 503
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "database": "error",
            "gcs": "error"
        }

@router.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes/Docker"""
    try:
        db_ready = test_db_connection()
        return {
            "ready": db_ready,
            "database": "ready" if db_ready else "not ready"
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "ready": False,
            "error": str(e)
        }