from fastapi import APIRouter
from .health_check import router as health_router
from .readiness import router as readiness_router

router = APIRouter(tags=["Health"])
router.include_router(health_router)
router.include_router(readiness_router)