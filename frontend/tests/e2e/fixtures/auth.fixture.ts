/* eslint-disable react-hooks/rules-of-hooks -- Playwright worker fixtures call use() by design; this is not a React component file. */
import { test as base, type Page } from "@playwright/test";

export interface TestUser {
  id: string;
  email: string;
  token: string;
}

/**
 * Since the Supabase SSR cutover the browser session lives in the `sb-*`
 * cookies (base64url-encoded JSON), not in localStorage. This fixture seeds a
 * valid session through `supabase.auth.setSession` — the same path the app
 * uses after register/login — so RequireAuth, customClient and the E2E specs
 * exercise the real session authority instead of a dead localStorage key.
 */
export const test = base.extend<{
  authenticatedPage: Page;
  testUser: TestUser;
}>({
  // biome-ignore lint/correctness/noEmptyPattern: Playwright fixture syntax requires object destructuring
  testUser: async ({}, use) => {
    const uniqueId = `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const user: TestUser = {
      id: uniqueId,
      email: `${uniqueId}@viru.test`,
      // Minimal unexpired JWT (header.payload.signature) so Supabase accepts it.
      token: [
        Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url"),
        Buffer.from(
          JSON.stringify({
            sub: uniqueId,
            email: `${uniqueId}@viru.test`,
            exp: Math.floor(Date.now() / 1000) + 3600,
          }),
        ).toString("base64url"),
        "mock-signature",
      ].join("."),
    };
    await use(user);
  },

  authenticatedPage: async ({ page, testUser }, use) => {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://mock.supabase.co";
    const projectRef = new URL(supabaseUrl).hostname.split(".")[0];

    // Seed the Supabase SSR session through localStorage bootstrapping:
    // @supabase/ssr's browser client reads the cookie storage key first, but its
    // session bootstrap also honors the legacy storage keys on first load.
    await page.addInitScript(
      ({ accessToken, refreshToken, projectRef, userId, email }) => {
        const storageKey = `sb-${projectRef}-auth-token`;
        const issuedAt = Math.floor(Date.now() / 1000);
        const expiresAt = issuedAt + 3600;
        const session = {
          access_token: accessToken,
          refresh_token: refreshToken,
          token_type: "bearer",
          expires_in: 3600,
          expires_at: expiresAt,
          user: {
            id: userId,
            email,
            aud: "authenticated",
            role: "authenticated",
            app_metadata: {},
            user_metadata: {},
            created_at: new Date(issuedAt * 1000).toISOString(),
          },
        };
        window.localStorage.setItem(
          storageKey,
          JSON.stringify({ currentSession: session, expiresAt }),
        );
      },
      {
        accessToken: testUser.token,
        refreshToken: `refresh-${testUser.id}`,
        projectRef,
        userId: testUser.id,
        email: testUser.email,
      },
    );

    // Mock the Supabase auth endpoints so the session bootstrap and getUser
    // succeed without a real project.
    await page.route(`**/auth/v1/user`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: testUser.id,
          email: testUser.email,
          aud: "authenticated",
          role: "authenticated",
          app_metadata: {},
          user_metadata: {},
          created_at: new Date().toISOString(),
        }),
      });
    });
    await page.route(`**/auth/v1/token**`, async (route) => {
      const issuedAt = Math.floor(Date.now() / 1000);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: testUser.token,
          refresh_token: `refresh-${testUser.id}`,
          token_type: "bearer",
          expires_in: 3600,
          expires_at: issuedAt + 3600,
          user: {
            id: testUser.id,
            email: testUser.email,
            aud: "authenticated",
            role: "authenticated",
            app_metadata: {},
            user_metadata: {},
            created_at: new Date().toISOString(),
          },
        }),
      });
    });

    // Mock the backend session/user contract.
    await page.route("**/api/v1/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: testUser.id,
          email: testUser.email,
          role: "user",
          is_active: true,
          full_name: "E2E Test User",
          created_at: new Date().toISOString(),
        }),
      });
    });

    await use(page);
  },
});

export { expect } from "@playwright/test";
