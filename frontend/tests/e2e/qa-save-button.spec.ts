import { test, expect } from "@playwright/test";

test("QA Save Flight Action", async ({ page }) => {
  await page.route("**/api/v1/search/quick*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        meta: {
          pagination: { total_results: 1, total_pages: 1 },
          provider_status: { overall: "ok", providers: [] }
        },
        results: [
          {
            result_id: "test-flight-1",
            origin: "MAD",
            destination: "BCN",
            travel_date: "2030-01-01",
            price: 50,
            currency: "EUR",
            departure_time_local: "2030-01-01T10:00:00",
            duration_total_min: 120,
            legs: []
          }
        ]
      })
    });
  });

  await page.route("**/api/v1/search/save-result", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        watch_id: "fake-watch-id-123",
        created_or_existing: "created",
        tracking_identity: "test-id",
        snapshot: null
      })
    });
  });
  
  await page.route("**/api/v1/watchlist", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([])
    });
  });

  await page.route("**/api/v1/airports/seeds*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { iata: "MAD", name: "Madrid", city: "Madrid", country: "ES" },
        { iata: "BCN", name: "Barcelona", city: "Barcelona", country: "ES" }
      ])
    });
  });

  // Navigate with pre-filled state
  await page.goto("/quick-search?origin=MAD&destination=BCN&date_out=2030-01-01");
  
  // The app will hydrate from URL. We still need to click Search.
  const submitBtn = page.locator('button[type="submit"], [data-testid="search-button"]');
  await submitBtn.waitFor({ state: 'visible' });
  await submitBtn.click();
  
  // Wait for results
  const saveBtn = page.locator('.qs-row-save').first();
  await saveBtn.waitFor({ state: 'visible', timeout: 5000 });
  
  // Click save
  await saveBtn.click();
  
  // Verify it turns into saved state (qs-row-saved)
  const savedIndicator = page.locator('.qs-row-saved').first();
  await expect(savedIndicator).toBeVisible({ timeout: 5000 });
  
  // Verify the toast notification appears
  // Toasts usually have role="status" or class names like .toast, .notification
  const toast = page.locator('div').filter({ hasText: /guardado|añadido|added|creado/i }).last();
  // We just wait for ANY toast container to be visible if the text is unpredictable
  await expect(page.locator('.toast, [role="status"], [role="alert"]').first()).toBeVisible({ timeout: 5000 });
});
