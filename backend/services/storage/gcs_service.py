import os
import uuid
from typing import Tuple
import json
from fastapi import HTTPException

try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    storage = None

class GCSService:
    def __init__(self):
        self.project_id = None
        self.bucket_name = None
        self.client = None
        self.bucket = None
        self._initialized = False

    def _initialize(self):
        if self._initialized:
            return
        if not GCS_AVAILABLE:
            raise HTTPException(status_code=500, detail="GCS libraries not available")
        self.project_id = os.getenv("GCS_PROJECT_ID")
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        if not self.project_id or not self.bucket_name:
            raise HTTPException(status_code=500, detail="GCS env vars missing")
        try:
            if os.getenv("GCS_SERVICE_ACCOUNT_KEY_BASE64"):
                import base64
                creds_json = json.loads(base64.b64decode(os.getenv("GCS_SERVICE_ACCOUNT_KEY_BASE64")).decode('utf-8'))
                self.client = storage.Client.from_service_account_info(creds_json, project=self.project_id)
            elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                self.client = storage.Client.from_service_account_json(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), project=self.project_id)
            else:
                self.client = storage.Client(project=self.project_id)
            self.bucket = self.client.bucket(self.bucket_name)
            self.bucket.reload()
            self._initialized = True
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to init GCS: {str(e)}")

    def upload_file(self, file_content: bytes, original_filename: str, mime_type: str, user_id: str) -> Tuple[str, str]:
        self._initialize()
        file_id = str(uuid.uuid4())
        ext = original_filename.split('.')[-1] if '.' in original_filename else ''
        filename = f"{file_id}.{ext}" if ext else file_id
        path = f"documents/{user_id}/{filename}"
        blob = self.bucket.blob(path)
        blob.upload_from_string(file_content, content_type=mime_type)
        return file_id, f"gs://{self.bucket_name}/{path}"

    def download_file(self, file_id: str, user_id: str) -> bytes:
        self._initialize()
        blobs = list(self.client.list_blobs(self.bucket_name, prefix=f"documents/{user_id}/"))
        for blob in blobs:
            if file_id in blob.name:
                return blob.download_as_bytes()
        raise HTTPException(status_code=404, detail="File not found")

    def delete_file(self, file_id: str, user_id: str) -> bool:
        self._initialize()
        blobs = list(self.client.list_blobs(self.bucket_name, prefix=f"documents/{user_id}/"))
        for blob in blobs:
            if file_id in blob.name:
                blob.delete()
                return True
        return False

    def get_file_metadata(self, file_id: str, user_id: str) -> dict:
        self._initialize()
        blobs = list(self.client.list_blobs(self.bucket_name, prefix=f"documents/{user_id}/"))
        for blob in blobs:
            if file_id in blob.name:
                blob.reload()
                return {
                    'name': blob.name,
                    'size': blob.size,
                    'content_type': blob.content_type,
                    'created': blob.time_created,
                    'updated': blob.updated
                }
        raise HTTPException(status_code=404, detail="File not found")

# Global instance
gcs_service = GCSService()