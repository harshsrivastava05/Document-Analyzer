import { NextRequest, NextResponse } from "next/server";
import { proxy } from "@/lib/api";
import { auth } from "@/lib/auth";

export async function GET() {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    let res;
    try {
      res = await proxy(`/documents?userId=${session.user.id}`);
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
      return NextResponse.json(
        { error: "Backend service unavailable", documents: [] },
        { status: 503 }
      );
    }

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('Documents API error:', error);
    return NextResponse.json(
      { error: "Failed to fetch documents", documents: [] },
      { status: 503 }
    );
  }
}
