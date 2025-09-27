from fastapi import APIRouter
from db.utils import test_db_connection, get_db_stats
from services.storage.gcs_service import gcs_service
import os, logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
async def health_check():
    db_ok = test_db_connection()
    gcs_ok = True
    try:
        if os.getenv("GCS_PROJECT_ID") and os.getenv("GCS_BUCKET_NAME"):
            gcs_service._initialize()
    except Exception as e:
        logger.warning(f"GCS health check failed: {e}")
        gcs_ok = False
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "gcs": "connected" if gcs_ok else "disconnected",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "stats": get_db_stats() if db_ok else {}
    }