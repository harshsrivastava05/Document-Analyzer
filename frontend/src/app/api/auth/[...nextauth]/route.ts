import { handlers } from "@/lib/auth"
export const { GET, POST } = handlers

// frontend/src/middleware.ts - Fix the import error
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

interface AuthRequest {
    nextUrl: URL
    auth?: unknown
    url: string
}

type AuthMiddleware = (req: AuthRequest) => NextResponse

const authMiddleware: AuthMiddleware = (req) => {
    const { pathname } = req.nextUrl

    // Public routes that don't require authentication
    if (pathname === "/" || pathname === "/login") {
        return NextResponse.next()
    }

    // Check if user is authenticated
    if (!req.auth) {
        // Redirect to login page
        return NextResponse.redirect(new URL("/login", req.url))
    }

    return NextResponse.next()
}

export default auth(authMiddleware)

export const config = {
  matcher: ["/((?!api/auth|_next/static|_next/image|favicon.ico).*)", "/"]
}