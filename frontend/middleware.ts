import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Hotfix stability middleware:
 * - Never intercept static assets or Next internals.
 * - Avoid returning 400s for chunk/css requests.
 * Auth is enforced at app level (RequireAuth) for now.
 */
export function middleware(_request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)"],
};
