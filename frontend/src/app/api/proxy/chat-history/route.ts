import { NextRequest, NextResponse } from "next/server";
import { proxy } from "@/lib/api";
import { auth } from "@/lib/auth";

export async function GET(req: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { searchParams } = new URL(req.url);
    const docId = searchParams.get("docId");
    
    const res = await proxy(
      `/chat-history?docId=${docId}&userId=${session.user.id}`
    );

    if (!res.ok) {
      console.error('Backend returned error:', res.status, res.statusText);
      return NextResponse.json(
        { error: "Backend service unavailable", messages: [] }, 
        { status: 503 }
      );
    }

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('Chat history API error:', error);
    return NextResponse.json(
      { error: "Failed to fetch chat history", messages: [] }, 
      { status: 503 }
    );
  }
}