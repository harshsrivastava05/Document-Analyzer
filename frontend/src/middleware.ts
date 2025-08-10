import { withAuth } from "next-auth/middleware";

export default withAuth(
  // `withAuth` augments your `Request` with the user's token.
  function middleware(req) {
    // Add any additional middleware logic here if needed
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        // Check if user is authenticated
        const { pathname } = req.nextUrl;
        
        // Allow access to public routes
        if (pathname === "/" || pathname === "/login") {
          return true;
        }
        
        // Require authentication for all other routes
        return !!token;
      },
    },
  }
);

export const config = {
  // Protect all routes except public ones and NextAuth routes
  matcher: ["/((?!api/auth|_next/static|_next/image|favicon.ico|$).*)"],
};