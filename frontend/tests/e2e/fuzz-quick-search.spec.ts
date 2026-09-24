import { test, expect } from "@playwright/test";

test("Check if form submits", async ({ page }) => {
  await page.goto("/quick-search");
  await page.waitForSelector('[data-testid="quick-search-form"]', { state: 'attached' }).catch(() => {});
  
  const submitBtn = page.locator('button[type="submit"], [data-testid="search-button"]');
  console.log("Submit button visible:", await submitBtn.isVisible());
  
  const reqPromise = page.waitForRequest(r => r.url().includes('/api/v1/search/quick') && r.method() === 'POST', { timeout: 3000 }).catch(e => e.message);
  await submitBtn.click();
  const req = await reqPromise;
  console.log("Request result:", typeof req === 'string' ? req : req?.url());
});
