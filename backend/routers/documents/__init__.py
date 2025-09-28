from fastapi import APIRouter
from . import list_docs, view_doc, delete_doc, upload

router = APIRouter()
router.include_router(list_docs.router)
router.include_router(view_doc.router)
router.include_router(delete_doc.router)
router.include_router(upload.router)