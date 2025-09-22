// frontend/src/app/api/upload-gcs/route.ts
import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { uploadFileToGCS } from "@/lib/gcs";
import { prisma } from "@/lib/prisma";

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id || !session?.user?.email) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const formData = await req.formData();
    const file = formData.get("file") as File;

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    // Validate file type
    const allowedTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain'
    ];

    if (!allowedTypes.includes(file.type)) {
      return NextResponse.json({ 
        error: "Invalid file type. Only PDF, DOC, DOCX, and TXT files are allowed." 
      }, { status: 400 });
    }

    // Validate file size (e.g., max 10MB)
    const maxSizeInMB = 10;
    if (file.size > maxSizeInMB * 1024 * 1024) {
      return NextResponse.json({ 
        error: `File size too large. Maximum size is ${maxSizeInMB}MB.` 
      }, { status: 400 });
    }

    // Ensure user exists in database before creating document
    try {
      await prisma.user.upsert({
        where: { email: session.user.email },
        update: {
          name: session.user.name,
          image: session.user.image,
        },
        create: {
          id: session.user.id,
          email: session.user.email,
          name: session.user.name,
          image: session.user.image,
        },
      });
    } catch (userError) {
      console.error("Error ensuring user exists:", userError);
      return NextResponse.json({ error: "Failed to create user record" }, { status: 500 });
    }

    // Convert file to buffer
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    // Upload to Google Cloud Storage
    const uploadResult = await uploadFileToGCS(
      buffer,
      file.name,
      file.type,
      session.user.id
    );

    // Save document record to database
    const document = await prisma.document.create({
      data: {
        userId: session.user.id,
        title: file.name,
        gcsFileId: uploadResult.fileId,
        gcsFilePath: uploadResult.publicUrl,
        mimeType: uploadResult.mimeType,
        fileSize: uploadResult.size,
        summary: "Processing...", // Will be updated by backend processing
      },
    });

    // Try to notify backend (optional - don't fail if backend is down)
    try {
      const backendResponse = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/process-document`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          documentId: document.id,
          userId: session.user.id,
          gcsFileId: uploadResult.fileId,
          fileName: file.name,
          mimeType: file.type,
        }),
        signal: AbortSignal.timeout(5000), // 5 second timeout
      });

      if (backendResponse.ok) {
        console.log('✅ Backend processing initiated');
      } else {
        console.warn('⚠️ Backend processing failed, but file was uploaded successfully');
      }
    } catch (error) {
      console.warn('⚠️ Failed to notify backend (server may be down):', error);
      // Don't fail the upload just because backend is down
    }

    return NextResponse.json({
      success: true,
      document: {
        id: document.id,
        title: document.title,
        fileId: uploadResult.fileId,
        size: uploadResult.size,
      },
      message: "File uploaded successfully and queued for processing"
    });

  } catch (error) {
    console.error("Upload error:", error);
    
    // Provide more specific error messages
    if (error instanceof Error) {
      if (error.message.includes('Foreign key constraint')) {
        return NextResponse.json(
          { error: "User authentication error. Please sign out and sign in again." },
          { status: 400 }
        );
      }
      if (error.message.includes('Google Cloud Storage')) {
        return NextResponse.json(
          { error: "File storage error. Please check your Google Cloud Storage configuration." },
          { status: 500 }
        );
      }
    }
    
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Upload failed" },
      { status: 500 }
    );
  }
}