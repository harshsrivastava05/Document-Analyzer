from fastapi import APIRouter
from .query import router as query_router

router = APIRouter(prefix="/chat", tags=["Chat"])
router.include_router(query_router)