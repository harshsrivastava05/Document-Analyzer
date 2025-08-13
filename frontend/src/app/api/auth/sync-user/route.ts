import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { id, email, name, image } = body;

    if (!email) {
      return NextResponse.json({ error: "Email is required" }, { status: 400 });
    }

    // Create or update user in database
    const user = await prisma.user.upsert({
      where: { email },
      update: {
        name,
        image,
      },
      create: {
        id,
        email,
        name,
        image,
      },
    });

    return NextResponse.json({ success: true, user });
  } catch (error) {
    console.error("Failed to sync user:", error);
    return NextResponse.json({ error: "Failed to sync user" }, { status: 500 });
  }
}
