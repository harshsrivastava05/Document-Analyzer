import 'dotenv/config'; 
import { Storage } from '@google-cloud/storage';
async function testGCSPermissions() {
  try {
    // Initialize storage (make sure your env vars are set)
    const storage = new Storage({
      projectId: process.env.GCS_PROJECT_ID,
      keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS,
    });

    const bucketName = process.env.GCS_BUCKET_NAME;
    const bucket = storage.bucket(bucketName);

    console.log(`Testing permissions for bucket: ${bucketName}`);

    // Test 1: Check if bucket exists and we can access it
    const [exists] = await bucket.exists();
    console.log(`✓ Bucket exists: ${exists}`);

    // Test 2: Try to create a test file
    const testFileName = 'test-permissions.txt';
    const testContent = 'This is a test file to verify GCS permissions.';
    
    const file = bucket.file(testFileName);
    await file.save(testContent, {
      metadata: {
        contentType: 'text/plain',
      },
    });
    
    console.log(`✓ Successfully created test file: ${testFileName}`);

    // Test 3: Try to read the file back
    const [content] = await file.download();
    console.log(`✓ Successfully read file content: ${content.toString()}`);

    // Test 4: Clean up - delete the test file
    await file.delete();
    console.log(`✓ Successfully deleted test file`);

    console.log('\n🎉 All tests passed! Your GCS permissions are working correctly.');
    
  } catch (error) {
    console.error('❌ GCS Permission test failed:', error.message);
    
    if (error.message.includes('403')) {
      console.log('\n💡 Fix suggestions:');
      console.log('1. Make sure your service account has Storage Object Admin role');
      console.log('2. Check that the bucket name is correct in your environment variables');
      console.log('3. Verify your service account key file path is correct');
    }
  }
}

testGCSPermissions();