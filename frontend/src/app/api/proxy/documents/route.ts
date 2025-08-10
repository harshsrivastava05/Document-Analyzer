import { NextRequest, NextResponse } from "next/server";
import { proxy } from "@/lib/api";
import { getServerSession } from "next-auth";
import authOptions from "@/lib/auth";

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session)
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const res = await proxy(`/documents?userId=${session.user.id}`);
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
