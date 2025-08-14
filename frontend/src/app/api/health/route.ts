// frontend/src/app/api/health/route.ts
import { NextResponse } from "next/server";
import { healthCheck } from "@/lib/api";

export async function GET() {
  try {
    const backendHealthy = await healthCheck();
    
    return NextResponse.json({
      frontend: "healthy",
      backend: backendHealthy ? "healthy" : "unhealthy",
      timestamp: new Date().toISOString(),
      backend_url: process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000"
    });
  } catch (error) {
    return NextResponse.json({
      frontend: "healthy",
      backend: "error",
      error: error instanceof Error ? error.message : "Unknown error",
      timestamp: new Date().toISOString(),
      backend_url: process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000"
    }, { status: 503 });
  }
}