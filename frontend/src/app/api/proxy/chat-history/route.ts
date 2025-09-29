// frontend/src/app/api/proxy/chat-history/route.ts
import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { createJWTForBackend } from "@/lib/jwt";

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { searchParams } = new URL(req.url);
    const docId = searchParams.get("docId");
    
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const url = `${backendUrl}/api/chat-history?docId=${docId}&userId=${session.user.id}`;
    
    // Create JWT token for backend authentication
    const jwtToken = createJWTForBackend(session.user.id);
    
    console.log('📡 Fetching chat history from:', url);
    console.log('🔑 Using JWT token for user:', session.user.id);

    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${jwtToken}`, // Add JWT token to Authorization header
      },
      signal: AbortSignal.timeout(10000), // 10 second timeout
    });

    if (!res.ok) {
      console.error('Backend returned error:', res.status, res.statusText);
      return NextResponse.json(
        { error: "Backend service unavailable", messages: [] }, 
        { status: 503 }
      );
    }

    const data = await res.json();
    console.log('✅ Chat history fetched successfully from backend');
    return NextResponse.json(data, { status: res.status });
    
  } catch (error) {
    console.error('Chat history API error:', error);
    return NextResponse.json(
      { error: "Failed to fetch chat history", messages: [] }, 
      { status: 503 }
    );
  }
}