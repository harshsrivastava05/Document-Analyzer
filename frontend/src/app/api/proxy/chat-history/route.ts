import { NextRequest, NextResponse } from "next/server";
import { proxy } from "@/lib/api";
import { getServerSession } from "next-auth";
import authOptions from "@/lib/auth";

export async function GET(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session)
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { searchParams } = new URL(req.url);
  const docId = searchParams.get("docId");
  const res = await proxy(
    `/chat-history?docId=${docId}&userId=${session.user.id}`
  );
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
