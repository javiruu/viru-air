/* eslint-disable react-hooks/rules-of-hooks -- Playwright worker fixtures call use() by design; this is not a React component file. */
import { test as base, type Page } from "@playwright/test";

export interface TestUser {
  id: string;
  email: string;
  token: string;
}

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
      token: `mock-jwt-token-${uniqueId}`,
    };
    await use(user);
  },

  authenticatedPage: async ({ page, testUser }, use) => {
    // Inject auth token before document loads
    await page.addInitScript(
      ({ token }) => {
        window.localStorage.setItem("sb_access_token", token);
        window.localStorage.setItem("sb_refresh_token", `refresh-${token}`);
      },
      { token: testUser.token },
    );

    // Mock /api/v1/auth/me response
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
