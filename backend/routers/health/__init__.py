from fastapi import APIRouter
from . import health_check, readiness

router = APIRouter()
router.include_router(health_check.router)
router.include_router(readiness.router)