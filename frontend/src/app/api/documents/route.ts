// frontend/src/app/api/documents/route.ts
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Get documents directly from database (fallback when backend is down)
    const documents = await prisma.document.findMany({
      where: {
        userId: session.user.id,
      },
      orderBy: {
        createdAt: 'desc',
      },
      select: {
        id: true,
        title: true,
        gcsFileId: true,
        mimeType: true,
        fileSize: true,
        summary: true,
        createdAt: true,
        updatedAt: true,
      },
    });

    return NextResponse.json({ 
      documents,
      source: "database" // Indicate this came from database, not backend
    });

  } catch (error) {
    console.error('Direct documents API error:', error);
    return NextResponse.json(
      { error: "Failed to fetch documents from database", documents: [] },
      { status: 500 }
    );
  }
}