# backend/test_gcs.py (CREATE THIS FILE)
"""
Test Google Cloud Storage connection and permissions
Run with: python test_gcs.py
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gcs_connection():
    """Test GCS connection and permissions"""
    print("🚀 Testing Google Cloud Storage connection...")
    
    # Check environment variables
    project_id = os.getenv("GCS_PROJECT_ID")
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    print(f"📍 Project ID: {project_id}")
    print(f"🪣 Bucket Name: {bucket_name}")
    print(f"🔑 Credentials Path: {credentials_path}")
    
    if not all([project_id, bucket_name, credentials_path]):
        print("❌ Missing required environment variables")
        return False
    
    # Check if credentials file exists
    if not os.path.exists(credentials_path):
        print(f"❌ Credentials file not found: {credentials_path}")
        return False
    
    try:
        from google.cloud import storage
        print("✅ Google Cloud Storage library imported successfully")
        
        # Initialize client
        client = storage.Client.from_service_account_json(credentials_path, project=project_id)
        print("✅ GCS client created successfully")
        
        # Test bucket access
        bucket = client.bucket(bucket_name)
        bucket.reload()  # This will fail if we don't have access
        print(f"✅ Successfully connected to bucket: {bucket_name}")
        
        # Test write permissions by creating a test file
        test_blob = bucket.blob("test/connection_test.txt")
        test_blob.upload_from_string("Hello, this is a connection test!", content_type="text/plain")
        print("✅ Successfully uploaded test file")
        
        # Test read permissions
        downloaded_content = test_blob.download_as_text()
        print(f"✅ Successfully downloaded test file: {downloaded_content[:50]}...")
        
        # Clean up test file
        test_blob.delete()
        print("✅ Successfully deleted test file")
        
        print("🎉 All GCS tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import Google Cloud Storage: {e}")
        print("Run: pip install google-cloud-storage")
        return False
        
    except Exception as e:
        print(f"❌ GCS test failed: {e}")
        
        # Provide specific error guidance
        if "403" in str(e):
            print("💡 This is a permissions error. Make sure your service account has:")
            print("   - Storage Admin role or Storage Object Admin role")
            print("   - Access to the bucket")
        elif "404" in str(e):
            print("💡 Bucket not found. Make sure:")
            print(f"   - Bucket '{bucket_name}' exists")
            print(f"   - It's in project '{project_id}'")
        
        return False

def test_backend_gcs():
    """Test the backend GCS service"""
    print("\n🔧 Testing backend GCS service...")
    
    try:
        from services.gcs_service import gcs_service
        
        # Test initialization
        gcs_service._initialize_client()
        print("✅ Backend GCS service initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Backend GCS service test failed: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("🧪 GOOGLE CLOUD STORAGE CONNECTION TEST")
    print("="*60)
    
    # Test direct GCS connection
    gcs_ok = test_gcs_connection()
    
    # Test backend service
    backend_ok = test_backend_gcs()
    
    # Summary
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    print(f"GCS Connection: {'✅ PASS' if gcs_ok else '❌ FAIL'}")
    print(f"Backend Service: {'✅ PASS' if backend_ok else '❌ FAIL'}")
    
    if gcs_ok and backend_ok:
        print("🎉 All tests passed! GCS is ready to use.")
    else:
        print("⚠️ Some tests failed. Please fix the issues above.")
        
        if not gcs_ok:
            print("\n💡 To fix GCS issues:")
            print("1. Check your service account permissions")
            print("2. Verify the bucket exists and is accessible")
            print("3. Make sure your credentials file is correct")
            print("4. Run the GCS setup script provided above")