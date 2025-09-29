// frontend/src/app/api/proxy/upload/route.ts
import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { createJWTForBackend } from "@/lib/jwt";

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const form = await req.formData();
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

    // Create JWT token for backend authentication
    const jwtToken = createJWTForBackend(session.user.id);

    console.log('🔑 Created JWT token for user:', session.user.id);
    console.log('📡 Uploading to:', `${backendUrl}/api/upload`);

    const res = await fetch(`${backendUrl}/api/upload`, { 
      method: "POST", 
      body: form,
      headers: {
        'Authorization': `Bearer ${jwtToken}`,
        // Don't set Content-Type for FormData - let fetch set it automatically
      }
    });

    if (!res.ok) {
      const errorText = await res.text();
      console.error('❌ Backend upload error:', res.status, errorText);
      
      try {
        const errorJson = JSON.parse(errorText);
        return NextResponse.json(
          { error: errorJson.detail || "Backend service unavailable" }, 
          { status: res.status }
        );
      } catch {
        return NextResponse.json(
          { error: `Backend error: ${res.status} ${res.statusText}` }, 
          { status: res.status }
        );
      }
    }

    const data = await res.json();
    console.log('✅ Upload successful:', data);
    return NextResponse.json(data, { status: res.status });
    
  } catch (error) {
    console.error('❌ Upload proxy API error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to upload file" }, 
      { status: 503 }
    );
  }
}