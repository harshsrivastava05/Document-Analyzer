from fastapi import APIRouter, UploadFile, File, HTTPException
from services.storage.gcs_service import gcs_service

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    content = await file.read()
    # This endpoint is generic; in your app prefer documents/upload which ties to user/docs.
    file_id, path = gcs_service.upload_file(content, file.filename, file.content_type or 'application/octet-stream', user_id="public")
    return {"file_id": file_id, "path": path}