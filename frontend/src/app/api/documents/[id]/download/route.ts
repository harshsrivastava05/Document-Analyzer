// frontend/src/app/api/documents/[id]/download/route.ts
import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { createJWTForBackend } from "@/lib/jwt";

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    const resolved = await context.params;
    const documentId = resolved.id;

    // Get document from database
    const document = await prisma.document.findFirst({
      where: {
        id: documentId,
        userId: session.user.id, // Ensure user owns the document
      },
    });

    if (!document) {
      return NextResponse.json({ error: "Document not found" }, { status: 404 });
    }

    // Proxy download from backend to avoid frontend GCS credentials
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const url = `${backendUrl}/api/documents/${documentId}/download`;
    const jwtToken = createJWTForBackend(session.user.id);

    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${jwtToken}`,
      },
      signal: AbortSignal.timeout(15000)
    });

    if (!res.ok) {
      const errText = await res.text();
      return NextResponse.json({ error: 'Backend download failed', details: errText }, { status: 502 });
    }

    const arrayBuffer = await res.arrayBuffer();
    const backendContentType = res.headers.get('content-type') || document.mimeType || 'application/octet-stream';

    const urlObj = new URL(req.url);
    const forceDownload = urlObj.searchParams.get('dl') === '1';

    const isPdf = backendContentType.includes('pdf') || (document.title?.toLowerCase().endsWith('.pdf'));

    // For PDFs: stream inline as before
    if (isPdf) {
      const contentDisposition = res.headers.get('content-disposition') || `inline; filename="${document.title || documentId}.pdf"`;
      return new NextResponse(Buffer.from(arrayBuffer) as BodyInit, {
        headers: {
          'Content-Type': 'application/pdf',
          'Content-Disposition': contentDisposition,
          'Content-Length': String(arrayBuffer.byteLength),
          'Accept-Ranges': 'bytes'
        },
      });
    }

    // For non-PDFs: if dl=1, return the binary to trigger download
    if (forceDownload) {
      const filename = document.title || `${documentId}`;
      return new NextResponse(Buffer.from(arrayBuffer) as BodyInit, {
        headers: {
          'Content-Type': backendContentType,
          'Content-Disposition': `attachment; filename="${filename}"`,
          'Content-Length': String(arrayBuffer.byteLength),
          'Accept-Ranges': 'bytes'
        }
      });
    }

    // Otherwise, return a lightweight HTML page inside the iframe to prevent auto-download
    const viewerHtml = `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Preview not available</title>
    <style>
      html,body{height:100%;margin:0;background:#0b0b0f;color:#e5e7eb;font-family:ui-sans-serif,system-ui,Segoe UI,Roboto,Helvetica,Arial}
      .wrap{height:100%;display:flex;align-items:center;justify-content:center;padding:16px;text-align:center}
      a{color:#a78bfa;text-decoration:underline}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div>
        <div style="font-size:16px;margin-bottom:8px">Inline preview is not supported for this file type.</div>
        <a href="${urlObj.pathname + '?dl=1'}" target="_parent" rel="noopener">Download to view</a>
      </div>
    </div>
  </body>
  </html>`;
    return new NextResponse(viewerHtml, {
      headers: { 'Content-Type': 'text/html; charset=utf-8' }
    });

  } catch (error) {
    console.error("Download error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Download failed" },
      { status: 500 }
    );
  }
}