import { withAuth } from "next-auth/middleware";
import { NextResponse } from "next/server";

export default withAuth(
  function middleware(req) {
    return NextResponse.next();
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        const { pathname } = req.nextUrl;
        
        // Public routes that don't require authentication
        const publicPaths = [
          "/", 
          "/login", 
          "/favicon.ico",
          "/api/auth/signin",
          "/api/auth/signout",
          "/api/auth/session",
          "/api/auth/providers",
          "/api/auth/callback/google"
        ];
        
        // Check if current path is public
        const isPublic = publicPaths.some((path) => pathname.startsWith(path));
        if (isPublic) return true;
        
        // For protected routes, require authentication
        return !!token;
      },
    },
  }
);

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api/auth (authentication routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - images (public images)
     */
    "/((?!api/auth|_next/static|_next/image|favicon.ico|images).*)",
  ],
};