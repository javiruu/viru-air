import { expect, test } from "./fixtures/auth.fixture";

test.describe("Quick Search Journey", () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    // Mock airports seed API
    await page.route("**/api/v1/airports/seeds*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          { iata: "MAD", name: "Madrid-Barajas", city: "Madrid", country: "ES" },
          { iata: "BCN", name: "Barcelona-El Prat", city: "Barcelona", country: "ES" },
          { iata: "PAR", name: "Paris Charles de Gaulle", city: "Paris", country: "FR" },
          { iata: "LON", name: "London Heathrow", city: "London", country: "GB" },
        ]),
      });
    });

    // Mock quick-search stream/execution endpoint
    await page.route("**/api/v1/search/quick-search*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          signature: "mad-bcn-mock-signature",
          origin: "MAD",
          destination: "BCN",
          results: [
            {
              id: "flight-1",
              origin: "MAD",
              destination: "BCN",
              price: 49.99,
              currency: "EUR",
              provider: "Ryanair",
              departure_time: "2026-10-15T08:30:00Z",
              arrival_time: "2026-10-15T09:50:00Z",
            },
          ],
        }),
      });
    });
  });

  test("loads quick-search view and airport pickers are accessible", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/quick-search");

    // Check main container
    const main = page.locator("main");
    await expect(main).toBeVisible();

    // Check airport picker button
    const originPickerButton = page
      .getByRole("button", { name: /Elegir aeropuerto de origen|Origen/i })
      .first();
    await expect(originPickerButton).toBeVisible({ timeout: 10_000 });
  });

  test("airport picker modal opens and closes properly", async ({ authenticatedPage: page }) => {
    await page.goto("/quick-search");
    const originPickerButton = page
      .getByRole("button", { name: /Elegir aeropuerto de origen|Origen/i })
      .first();
    await expect(originPickerButton).toBeVisible();
    await originPickerButton.click();

    // Dialog should open
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    // Closing via escape key or overlay
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden({ timeout: 5_000 });
  });
});
