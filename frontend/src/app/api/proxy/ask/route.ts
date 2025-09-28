// frontend/src/app/api/proxy/ask/route.ts
import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { createJWTForBackend } from "@/lib/jwt";

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const url = `${backendUrl}/api/ask`;
    
    // Create JWT token for backend authentication
    const jwtToken = createJWTForBackend(session.user.id);
    
    console.log('📡 Sending question to backend:', url);
    console.log('🔑 Using JWT token for user:', session.user.id);

    const res = await fetch(url, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        'Authorization': `Bearer ${jwtToken}`, // Add JWT token to Authorization header
      },
      body: JSON.stringify({ ...body, userId: session.user.id }),
      signal: AbortSignal.timeout(30000), // 30 second timeout for AI processing
    });

    if (!res.ok) {
      console.error('Backend returned error:', res.status, res.statusText);
      const errorText = await res.text();
      console.error('Backend error details:', errorText);
      
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
    console.log('✅ Question processed successfully by backend');
    return NextResponse.json(data, { status: res.status });
    
  } catch (error) {
    console.error('Ask API error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to process question" }, 
      { status: 503 }
    );
  }
}