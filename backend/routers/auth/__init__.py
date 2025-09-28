from fastapi import APIRouter
from . import login, register, profile, tokens

router = APIRouter()
router.include_router(login.router)
router.include_router(register.router)
router.include_router(profile.router)
router.include_router(tokens.router)