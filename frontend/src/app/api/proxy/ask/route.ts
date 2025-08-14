import { NextRequest, NextResponse } from "next/server";
import { proxy } from "@/lib/api";
import { auth } from "@/lib/auth";

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const res = await proxy("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, userId: session.user.id }),
    });

    if (!res.ok) {
      console.error('Backend returned error:', res.status, res.statusText);
      return NextResponse.json(
        { error: "Backend service unavailable" }, 
        { status: 503 }
      );
    }

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('Ask API error:', error);
    return NextResponse.json(
      { error: "Failed to process question" }, 
      { status: 503 }
    );
  }
}