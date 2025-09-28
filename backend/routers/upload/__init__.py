from fastapi import APIRouter
from . import upload_file, download_file, delete_file

router = APIRouter()
router.include_router(upload_file.router)
router.include_router(download_file.router)
router.include_router(delete_file.router)