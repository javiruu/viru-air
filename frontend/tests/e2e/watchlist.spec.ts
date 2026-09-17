import { expect, test } from "./fixtures/auth.fixture";

test.describe("Watchlist Journey", () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    // Mock watchlist list API
    await page.route("**/api/v1/watchlist*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 1,
            origin: "MAD",
            destination: "BCN",
            target_price: 50.0,
            active: true,
            current_price: 45.0,
            currency: "EUR",
            created_at: new Date().toISOString(),
          },
        ]),
      });
    });
  });

  test("watchlist page renders cleanly with active items", async ({ authenticatedPage: page }) => {
    await page.goto("/watchlist");
    const main = page.locator("main");
    await expect(main).toBeVisible();
  });
});
