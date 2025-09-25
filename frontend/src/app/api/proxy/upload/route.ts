// frontend/src/app/api/proxy/upload/route.ts
import { NextRequest, NextResponse } from "next/server";
import { proxy } from "@/lib/api";
import { auth } from "@/lib/auth";

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const form = await req.formData();
    form.append("userId", session.user.id);

    // Create JWT token for backend authentication (if your backend expects it)
    // You might need to implement this based on your auth system
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

    const res = await fetch(`${backendUrl}/api/upload`, { 
      method: "POST", 
      body: form,
      // Remove Content-Type header for FormData - let the browser set it
      headers: {
        // Add any authentication headers your backend expects
        // 'Authorization': `Bearer ${jwtToken}`, // If needed
      }
    });

    if (!res.ok) {
      const errorText = await res.text();
      console.error('Backend upload error:', res.status, errorText);
      
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
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('Upload proxy API error:', error);
    
    // Provide specific error messages based on error type
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return NextResponse.json(
        { error: "Unable to connect to backend service. Please check if the backend is running." }, 
        { status: 503 }
      );
    }
    
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to upload file" }, 
      { status: 503 }
    );
  }
}