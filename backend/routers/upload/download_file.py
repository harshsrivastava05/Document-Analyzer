from fastapi import APIRouter, HTTPException
from services.storage.gcs_service import gcs_service

router = APIRouter()

@router.get("/download/{file_id}")
async def download_file(file_id: str):
    try:
        content = gcs_service.download_file(file_id, user_id="public")
        from fastapi.responses import Response
        return Response(content=content, media_type='application/octet-stream')
    except HTTPException:
        raise