import { NextRequest, NextResponse } from "next/server";
import { proxy } from "@/lib/api";
import { auth } from "@/lib/auth";

export async function GET() {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const res = await proxy(`/documents?userId=${session.user.id}`);
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}