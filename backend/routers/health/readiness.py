from fastapi import APIRouter
from db.utils import test_db_connection

router = APIRouter()

@router.get("/ready")
async def readiness_check():
    ready = test_db_connection()
    return {"ready": ready, "database": "ready" if ready else "not ready"}