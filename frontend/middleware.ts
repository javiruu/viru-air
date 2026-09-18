import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

/**
 * Supabase SSR session refresh middleware.
 *
 * The `(private)` routes rely on the Supabase session stored in cookies. On a
 * long-lived session the access token expires; without this middleware the
 * server-side helpers (lib/supabase/server.ts) would read an expired token
 * with no way to hand the refreshed cookies back to the browser. Following the
 * documented @supabase/ssr pattern, every matched request creates a server
 * client bound to the request/response cookie cycle so token refreshes are
 * persisted before the response is sent.
 *
 * Page-level auth remains enforced by RequireAuth; this middleware only keeps
 * the session cookies fresh.
 */
export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  // Skip silently when Supabase is not configured (e.g. offline test builds);
  // the browser client falls back to a mock project in those environments.
  if (!supabaseUrl || !supabaseKey) {
    return response;
  }

  const supabase = createServerClient(supabaseUrl, supabaseKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options),
        );
      },
    },
  });

  // Triggers the token refresh when the access token is expired or near expiry.
  // getUser (not getSession) validates the token against the auth server.
  await supabase.auth.getUser();

  return response;
}

export const config = {
  matcher: [
    /*
     * Match everything except Next internals and static assets so session
     * cookies stay fresh across app and API routes without intercepting
     * chunk/css/image requests.
     */
    "/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|icon.png|brand/).*)",
  ],
};
