// frontend/src/app/api/proxy/documents/route.ts
import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { createJWTForBackend } from "@/lib/jwt";

export async function GET() {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const url = `${backendUrl}/api/documents`;
    
    // Create JWT token for backend authentication using existing function
    const jwtToken = createJWTForBackend(session.user.id);
    
    console.log('📡 Fetching documents from backend:', url);
    console.log('🔑 Using JWT authentication for user:', session.user.id);

    let res;
    try {
      res = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${jwtToken}`,  // Add JWT authentication
        },
        signal: AbortSignal.timeout(15000), // 15 second timeout
      });
    } catch (error) {
      console.error('Backend connection failed:', error);
      let errorMsg = 'Connection timeout or network error';
      if (error instanceof Error) {
        errorMsg = error.message;
      }
      return NextResponse.json(
        { error: `Backend unavailable: ${errorMsg}`, documents: [] },
        { status: 503 }
      );
    }

    if (!res.ok) {
      console.error('Backend returned error:', res.status, res.statusText);
      const errorText = await res.text();
      console.error('Backend error details:', errorText);
      
      // Try to parse error as JSON
      let errorDetails = errorText;
      try {
        const errorJson = JSON.parse(errorText);
        errorDetails = errorJson.detail || errorText;
      } catch {
        // Keep original error text
      }
      
      // Specific handling for authentication errors
      if (res.status === 403 || res.status === 401) {
        console.error('🔐 Authentication failed - check JWT token');
        return NextResponse.json(
          { error: "Authentication failed", documents: [], details: errorDetails },
          { status: 403 }
        );
      }
      
      return NextResponse.json(
        { error: "Backend service error", documents: [], details: errorDetails },
        { status: res.status }
      );
    }

    const data = await res.json();
    console.log('✅ Documents fetched successfully from backend:', data.documents?.length || 0, 'documents');
    
    // Log first few document IDs for debugging
    if (data.documents && data.documents.length > 0) {
      console.log('📄 Sample document IDs:', data.documents.slice(0, 3).map((d: any) => d.id));
    }
    
    return NextResponse.json(data, { status: res.status });
    
  } catch (error) {
    console.error('Documents API error:', error);
    return NextResponse.json(
      { error: "Internal proxy error", documents: [] },
      { status: 500 }
    );
  }
}