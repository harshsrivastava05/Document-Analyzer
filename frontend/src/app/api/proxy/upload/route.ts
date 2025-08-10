import { NextRequest, NextResponse } from "next/server";
import { proxy } from "@/lib/api";
import { auth } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const form = await req.formData();
  form.append("userId", session.user.id);

  const res = await proxy("/upload", { method: "POST", body: form as any });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}