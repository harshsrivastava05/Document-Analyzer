from fastapi import APIRouter
from services.storage.gcs_service import gcs_service

router = APIRouter()

@router.delete("/{file_id}")
async def delete_file(file_id: str):
    ok = gcs_service.delete_file(file_id, user_id="public")
    return {"deleted": ok}