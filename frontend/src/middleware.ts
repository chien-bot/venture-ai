import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Only check if a token exists — role enforcement is done client-side
  // using sessionStorage (which is tab-isolated), allowing student and
  // teacher portals to be open simultaneously in different browser tabs.
  const token = request.cookies.get("token")?.value;

  const isProtectedRoute = pathname.startsWith("/teacher") || pathname.startsWith("/student");

  // Not logged in → redirect to login
  if (isProtectedRoute && !token) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/student/:path*", "/teacher/:path*"],
};
