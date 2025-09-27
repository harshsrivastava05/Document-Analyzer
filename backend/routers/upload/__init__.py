from fastapi import APIRouter
from .upload_file import router as upload_router
from .download_file import router as download_router
from .delete_file import router as delete_router

router = APIRouter(prefix="/uploads", tags=["Uploads"])
router.include_router(upload_router)
router.include_router(download_router)
router.include_router(delete_router)