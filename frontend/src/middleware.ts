import { auth } from "@/lib/auth";

export default auth((req) => {
  const { nextUrl } = req;
  const isLoggedIn = !!req.auth;

  // Define routes that don't require authentication
  const publicRoutes = ["/", "/login", "/error"];
  const apiRoutes = nextUrl.pathname.startsWith("/api");

  // Allow public routes and API routes
  if (publicRoutes.includes(nextUrl.pathname) || apiRoutes) {
    return;
  }

  // Redirect to login if not authenticated
  if (!isLoggedIn) {
    const loginUrl = new URL("/login", nextUrl);
    return Response.redirect(loginUrl);
  }

  // Allow access to protected routes if authenticated
});

export const config = {
  matcher: [
    // Match all request paths except static files and images
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
