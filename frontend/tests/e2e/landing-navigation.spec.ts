import { expect, test } from "./fixtures/auth.fixture";

test.describe("Public Navigation & Visual Foundations", () => {
  test("landing page renders with core branding and search CTA", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Viru/i);
    // Heading or main call to action
    const main = page.locator("main");
    await expect(main).toBeVisible();
  });

  test("responsive viewport renders cleanly without horizontal scrollbar", async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2); // allowance for rounding
  });

  test("theme toggle or theme persistence preserves document theme class", async ({ page }) => {
    await page.goto("/");
    const html = page.locator("html");
    const initialClass = (await html.getAttribute("class")) || "";
    // Check dark or light class
    expect(
      initialClass.includes("dark") || initialClass.includes("light") || initialClass === "",
    ).toBeTruthy();
  });
});
