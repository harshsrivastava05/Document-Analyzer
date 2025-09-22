import { Storage } from '@google-cloud/storage';
import { v4 as uuidv4 } from 'uuid';
import 'dotenv/config'; 

// Initialize Google Cloud Storage
let storage: Storage;

function initializeStorage() {
  if (storage) return storage;

  const projectId = process.env.GCS_PROJECT_ID;
  const bucketName = process.env.GCS_BUCKET_NAME;

  if (!projectId || !bucketName) {
    throw new Error('GCS_PROJECT_ID and GCS_BUCKET_NAME environment variables are required');
  }

  // Three ways to authenticate:
  // 1. Using base64 encoded service account key (for deployment)
  if (process.env.GCS_SERVICE_ACCOUNT_KEY_BASE64) {
    try {
      const credentials = JSON.parse(
        Buffer.from(process.env.GCS_SERVICE_ACCOUNT_KEY_BASE64, 'base64').toString()
      );
      storage = new Storage({
        projectId,
        credentials,
      });
      console.log('✅ Using base64 encoded service account key');
    } catch (error) {
      console.error('❌ Error parsing base64 service account key:', error);
      throw new Error('Invalid base64 service account key');
    }
  }
  // 2. Using service account key file path
  else if (process.env.GOOGLE_APPLICATION_CREDENTIALS) {
    storage = new Storage({
      projectId,
      keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS,
    });
    console.log('✅ Using service account key file');
  }
  // 3. Default credentials (when running on GCP)
  else {
    storage = new Storage({ projectId });
    console.log('✅ Using default credentials');
  }

  return storage;
}

export interface UploadResult {
  fileId: string;
  fileName: string;
  mimeType: string;
  size: number;
  publicUrl?: string;
}

export async function uploadFileToGCS(
  file: Buffer,
  originalName: string,
  mimeType: string,
  userId: string
): Promise<UploadResult> {
  const gcs = initializeStorage();
  const bucketName = process.env.GCS_BUCKET_NAME!;
  const bucket = gcs.bucket(bucketName);

  // Generate unique file ID and create folder structure
  const fileId = uuidv4();
  const fileExtension = originalName.split('.').pop();
  const fileName = `${fileId}.${fileExtension}`;
  const filePath = `documents/${userId}/${fileName}`;

  const gcsFile = bucket.file(filePath);

  try {
    // Upload the file
    await gcsFile.save(file, {
      metadata: {
        contentType: mimeType,
        metadata: {
          originalName,
          userId,
          uploadedAt: new Date().toISOString(),
        },
      },
    });

    console.log(`File uploaded successfully: ${filePath}`);

    return {
      fileId,
      fileName: originalName,
      mimeType,
      size: file.length,
      publicUrl: `gs://${bucketName}/${filePath}`,
    };
  } catch (error) {
    console.error('Error uploading file to GCS:', error);
    throw new Error('Failed to upload file to Google Cloud Storage');
  }
}

export async function downloadFileFromGCS(fileId: string, userId: string): Promise<Buffer> {
  const gcs = initializeStorage();
  const bucketName = process.env.GCS_BUCKET_NAME!;
  const bucket = gcs.bucket(bucketName);

  // Find the file by scanning the user's directory
  const [files] = await bucket.getFiles({
    prefix: `documents/${userId}/`,
  });

  const targetFile = files.find(file => file.name.includes(fileId));

  if (!targetFile) {
    throw new Error(`File with ID ${fileId} not found`);
  }

  try {
    const [fileBuffer] = await targetFile.download();
    return fileBuffer;
  } catch (error) {
    console.error('Error downloading file from GCS:', error);
    throw new Error('Failed to download file from Google Cloud Storage');
  }
}

export async function deleteFileFromGCS(fileId: string, userId: string): Promise<void> {
  const gcs = initializeStorage();
  const bucketName = process.env.GCS_BUCKET_NAME!;
  const bucket = gcs.bucket(bucketName);

  // Find the file by scanning the user's directory
  const [files] = await bucket.getFiles({
    prefix: `documents/${userId}/`,
  });

  const targetFile = files.find(file => file.name.includes(fileId));

  if (!targetFile) {
    throw new Error(`File with ID ${fileId} not found`);
  }

  try {
    await targetFile.delete();
    console.log(`File deleted successfully: ${targetFile.name}`);
  } catch (error) {
    console.error('Error deleting file from GCS:', error);
    throw new Error('Failed to delete file from Google Cloud Storage');
  }
}

export async function getFileMetadata(fileId: string, userId: string) {
  const gcs = initializeStorage();
  const bucketName = process.env.GCS_BUCKET_NAME!;
  const bucket = gcs.bucket(bucketName);

  // Find the file by scanning the user's directory
  const [files] = await bucket.getFiles({
    prefix: `documents/${userId}/`,
  });

  const targetFile = files.find(file => file.name.includes(fileId));

  if (!targetFile) {
    throw new Error(`File with ID ${fileId} not found`);
  }

  try {
    const [metadata] = await targetFile.getMetadata();
    return {
      name: metadata.metadata?.originalName || targetFile.name,
      size: parseInt(metadata.size as string || '0'),
      contentType: metadata.contentType,
      created: metadata.timeCreated,
      updated: metadata.updated,
    };
  } catch (error) {
    console.error('Error getting file metadata from GCS:', error);
    throw new Error('Failed to get file metadata from Google Cloud Storage');
  }
}