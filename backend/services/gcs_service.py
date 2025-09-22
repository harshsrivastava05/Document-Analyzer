import os
import uuid
from typing import Tuple, Optional
import json
from fastapi import HTTPException

# Only import Google Cloud if credentials are available
try:
    from google.cloud import storage
    from google.cloud.exceptions import NotFound
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    storage = None
    NotFound = None

class GCSService:
    def __init__(self):
        # Initialize all attributes but don't connect yet
        self.project_id = None
        self.bucket_name = None
        self.client = None
        self.bucket = None
        self._initialized = False
        self._initialization_attempted = False
    
    def _initialize_client(self):
        """Initialize Google Cloud Storage client (lazy initialization)"""
        # Only try to initialize once
        if self._initialization_attempted:
            if not self._initialized:
                raise HTTPException(status_code=500, detail="GCS initialization failed previously")
            return
        
        self._initialization_attempted = True
        
        if not GCS_AVAILABLE:
            raise HTTPException(
                status_code=500, 
                detail="Google Cloud Storage libraries not available. Please install google-cloud-storage."
            )
        
        self.project_id = os.getenv("GCS_PROJECT_ID")
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        
        if not self.project_id:
            raise HTTPException(
                status_code=500, 
                detail="GCS_PROJECT_ID environment variable is not set. Please check your .env file."
            )
            
        if not self.bucket_name:
            raise HTTPException(
                status_code=500, 
                detail="GCS_BUCKET_NAME environment variable is not set. Please check your .env file."
            )
        
        try:
            # Try different authentication methods
            if os.getenv("GCS_SERVICE_ACCOUNT_KEY_BASE64"):
                # Method 1: Base64 encoded service account key
                import base64
                try:
                    credentials_json = json.loads(
                        base64.b64decode(os.getenv("GCS_SERVICE_ACCOUNT_KEY_BASE64")).decode('utf-8')
                    )
                    self.client = storage.Client.from_service_account_info(
                        credentials_json, project=self.project_id
                    )
                    print("✅ Using base64 encoded service account key for GCS")
                except Exception as e:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Failed to decode base64 service account key: {str(e)}"
                    )
                    
            elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                # Method 2: Service account key file
                credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if not os.path.exists(credentials_path):
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Service account key file not found: {credentials_path}. Please check the path in your .env file."
                    )
                try:
                    self.client = storage.Client.from_service_account_json(
                        credentials_path, 
                        project=self.project_id
                    )
                    print("✅ Using service account key file for GCS")
                except Exception as e:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Failed to load service account key file: {str(e)}"
                    )
            else:
                # Method 3: Default credentials (when running on GCP)
                try:
                    self.client = storage.Client(project=self.project_id)
                    print("✅ Using default credentials for GCS")
                except Exception as e:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"No valid GCS credentials found. Please set GOOGLE_APPLICATION_CREDENTIALS or GCS_SERVICE_ACCOUNT_KEY_BASE64 in your .env file. Error: {str(e)}"
                    )
            
            # Test the connection
            try:
                self.bucket = self.client.bucket(self.bucket_name)
                # Try to check if bucket exists
                self.bucket.reload()
                self._initialized = True
                print(f"✅ GCS initialized successfully with bucket: {self.bucket_name}")
                
            except NotFound:
                raise HTTPException(
                    status_code=500, 
                    detail=f"GCS bucket '{self.bucket_name}' not found. Please check the bucket name in your .env file."
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to access GCS bucket '{self.bucket_name}': {str(e)}"
                )
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Failed to initialize GCS client: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to initialize Google Cloud Storage: {str(e)}"
            )
    
    def upload_file(self, file_content: bytes, original_filename: str, 
                   mime_type: str, user_id: str) -> Tuple[str, str]:
        """Upload file to Google Cloud Storage"""
        try:
            self._initialize_client()  # Initialize on first use
            
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
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ GCS upload failed: {e}")
            raise HTTPException(status_code=500, detail=f"File upload to GCS failed: {str(e)}")
    
    def download_file(self, file_id: str, user_id: str) -> bytes:
        """Download file from Google Cloud Storage"""
        try:
            self._initialize_client()  # Initialize on first use
            
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
            
        except HTTPException:
            raise
        except NotFound:
            raise HTTPException(status_code=404, detail="File not found")
        except Exception as e:
            print(f"❌ GCS download failed: {e}")
            raise HTTPException(status_code=500, detail=f"File download failed: {str(e)}")
    
    def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete file from Google Cloud Storage"""
        try:
            self._initialize_client()  # Initialize on first use
            
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
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ GCS delete failed: {e}")
            raise HTTPException(status_code=500, detail=f"File deletion failed: {str(e)}")
    
    def get_file_metadata(self, file_id: str, user_id: str) -> dict:
        """Get file metadata from Google Cloud Storage"""
        try:
            self._initialize_client()  # Initialize on first use
            
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
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ GCS metadata failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get file metadata: {str(e)}")

# Global instance - safe to create without initialization
gcs_service = GCSService()