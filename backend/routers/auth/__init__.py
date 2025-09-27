from fastapi import APIRouter
from .login import router as login_router
from .register import router as register_router
from .profile import router as profile_router
from .tokens import router as tokens_router

router = APIRouter(prefix="/auth", tags=["Authentication"])
router.include_router(login_router)
router.include_router(register_router)
router.include_router(profile_router)
router.include_router(tokens_router)