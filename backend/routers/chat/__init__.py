from fastapi import APIRouter
from . import query

router = APIRouter()
router.include_router(query.router)