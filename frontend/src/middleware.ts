import { auth } from "@/lib/auth";

export default auth((req) => {
  const { nextUrl } = req;
  const isLoggedIn = !!req.auth;

  // Define public routes that don't require authentication
  const publicRoutes = ["/", "/login"];
  const isPublicRoute = publicRoutes.includes(nextUrl.pathname);

  // Allow access to public routes
  if (isPublicRoute) {
    return;
  }

  // Redirect to login if not authenticated
  if (!isLoggedIn) {
    return Response.redirect(new URL("/login", nextUrl));
  }

  // Allow access to protected routes if authenticated
  return;
});

export const config = {
  // Protect all routes except public ones, API routes, and static files
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};