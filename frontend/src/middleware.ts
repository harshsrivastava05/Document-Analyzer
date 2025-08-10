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
        // Public routes:
        const publicPaths = ["/", "/login", "/favicon.ico"];
        const isPublic = publicPaths.some((p) => pathname === p);
        if (isPublic) return true;
        // Everything else requires auth
        return !!token;
      },
    },
  }
);

export const config = {
  matcher: ["/((?!_next/static|_next/image|images|favicon.ico|api/auth).*)"],
};
