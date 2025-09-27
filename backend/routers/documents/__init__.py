from fastapi import APIRouter
from .list_docs import router as list_router
from .view_doc import router as view_router
from .delete_doc import router as delete_router
from .upload import router as upload_router

router = APIRouter(prefix="/documents", tags=["Documents"])
router.include_router(list_router)
router.include_router(view_router)
router.include_router(delete_router)
router.include_router(upload_router)