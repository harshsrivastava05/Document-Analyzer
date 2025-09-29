// frontend/src/app/api/proxy/documents/route.ts
import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { createJWTForBackend } from "@/lib/jwt";

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const url = `${backendUrl}/api/documents?userId=${session.user.id}`;
    
    // Create JWT token for backend authentication
    const jwtToken = createJWTForBackend(session.user.id);
    
    console.log('📡 Fetching documents from:', url);
    console.log('🔑 Using JWT token for user:', session.user.id);

    let res;
    try {
      res = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${jwtToken}`, // Add JWT token to Authorization header
        },
        signal: AbortSignal.timeout(10000), // 10 second timeout
      });
    } catch (error) {
      console.error('Backend connection failed:', error);
      let errorMsg = 'Unknown error';
      if (error instanceof Error) {
        errorMsg = error.message;
      } else if (typeof error === 'string') {
        errorMsg = error;
      }
      return NextResponse.json(
        { error: `Backend connection failed: ${errorMsg}`, documents: [] },
        { status: 503 }
      );
    }

    if (!res.ok) {
      console.error('Backend returned error:', res.status, res.statusText);
      const errorText = await res.text();
      console.error('Backend error details:', errorText);
      
      return NextResponse.json(
        { error: "Backend service unavailable", documents: [], details: errorText },
        { status: 503 }
      );
    }

    const data = await res.json();
    console.log('✅ Documents fetched successfully from backend:', data.documents?.length || 0, 'documents');
    return NextResponse.json(data, { status: res.status });
    
  } catch (error) {
    console.error('Documents API error:', error);
    return NextResponse.json(
      { error: "Failed to fetch documents", documents: [] },
      { status: 503 }
    );
  }
}