import os
import uuid
from google.cloud import storage
from google.cloud.exceptions import NotFound
import tempfile
from typing import Tuple, Optional
import json
from fastapi import HTTPException

class GCSService:
    def __init__(self):
        self.project_id = os.getenv("GCS_PROJECT_ID")
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        self.client = None
        self.bucket = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Cloud Storage client"""
        if not self.project_id or not self.bucket_name:
            raise ValueError("GCS_PROJECT_ID and GCS_BUCKET_NAME must be set")
        
        try:
            # Try different authentication methods
            if os.getenv("GCS_SERVICE_ACCOUNT_KEY_BASE64"):
                # Method 1: Base64 encoded service account key
                credentials_json = json.loads(
                    os.getenv("GCS_SERVICE_ACCOUNT_KEY_BASE64").encode().decode('base64')
                )
                self.client = storage.Client.from_service_account_info(
                    credentials_json, project=self.project_id
                )
                print("✅ Using base64 encoded service account key for GCS")
            elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                # Method 2: Service account key file
                self.client = storage.Client.from_service_account_json(
                    os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), 
                    project=self.project_id
                )
                print("✅ Using service account key file for GCS")
            else:
                # Method 3: Default credentials (when running on GCP)
                self.client = storage.Client(project=self.project_id)
                print("✅ Using default credentials for GCS")
            
            self.bucket = self.client.bucket(self.bucket_name)
            
        except Exception as e:
            print(f"❌ Failed to initialize GCS client: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize Google Cloud Storage")
    
    def upload_file(self, file_content: bytes, original_filename: str, 
                   mime_type: str, user_id: str) -> Tuple[str, str]:
        """Upload file to Google Cloud Storage"""
        try:
            file_id = str(uuid.uuid4())
            file_extension = original_filename.split('.')[-1] if '.' in original_filename else ''
            filename = f"{file_id}.{file_extension}" if file_extension else file_id
            blob_path = f"documents/{user_id}/{filename}"
            
            blob = self.bucket.blob(blob_path)
            blob.metadata = {
                'original_filename': original_filename,
                'user_id': user_id,
                'uploaded_at': str(uuid.uuid1().time)
            }
            
            blob.upload_from_string(file_content, content_type=mime_type)
            
            print(f"✅ File uploaded to GCS: {blob_path}")
            return file_id, f"gs://{self.bucket_name}/{blob_path}"
            
        except Exception as e:
            print(f"❌ GCS upload failed: {e}")
            raise HTTPException(status_code=500, detail="File upload to GCS failed")
    
    def download_file(self, file_id: str, user_id: str) -> bytes:
        """Download file from Google Cloud Storage"""
        try:
            # Find the file by scanning the user's directory
            blobs = list(self.client.list_blobs(
                self.bucket_name, 
                prefix=f"documents/{user_id}/"
            ))
            
            target_blob = None
            for blob in blobs:
                if file_id in blob.name:
                    target_blob = blob
                    break
            
            if not target_blob:
                raise HTTPException(status_code=404, detail="File not found")
            
            return target_blob.download_as_bytes()
            
        except NotFound:
            raise HTTPException(status_code=404, detail="File not found")
        except Exception as e:
            print(f"❌ GCS download failed: {e}")
            raise HTTPException(status_code=500, detail="File download failed")
    
    def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete file from Google Cloud Storage"""
        try:
            # Find and delete the file
            blobs = list(self.client.list_blobs(
                self.bucket_name, 
                prefix=f"documents/{user_id}/"
            ))
            
            for blob in blobs:
                if file_id in blob.name:
                    blob.delete()
                    print(f"✅ File deleted from GCS: {blob.name}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ GCS delete failed: {e}")
            raise HTTPException(status_code=500, detail="File deletion failed")
    
    def get_file_metadata(self, file_id: str, user_id: str) -> dict:
        """Get file metadata from Google Cloud Storage"""
        try:
            blobs = list(self.client.list_blobs(
                self.bucket_name, 
                prefix=f"documents/{user_id}/"
            ))
            
            for blob in blobs:
                if file_id in blob.name:
                    blob.reload()
                    return {
                        'name': blob.metadata.get('original_filename', blob.name) if blob.metadata else blob.name,
                        'size': blob.size,
                        'content_type': blob.content_type,
                        'created': blob.time_created,
                        'updated': blob.updated
                    }
            
            raise HTTPException(status_code=404, detail="File not found")
            
        except Exception as e:
            print(f"❌ GCS metadata failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to get file metadata")

# Global instance
gcs_service = GCSService()