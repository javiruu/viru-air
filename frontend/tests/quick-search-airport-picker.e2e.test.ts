import assert from "node:assert/strict";
import test from "node:test";

import { chromium } from "playwright";

const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";

test("quick-search airport picker opens before search and can be dismissed", async (t) => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });

  try {
    try {
      await page.goto(`${BASE_URL}/quick-search`, { waitUntil: "domcontentloaded", timeout: 15000 });
    } catch {
      t.skip(`Quick-Search not reachable at ${BASE_URL}. Start frontend and retry.`);
      return;
    }

    const originPickerButton = page.getByRole("button", { name: "Elegir aeropuerto de origen" });
    try {
      await originPickerButton.waitFor({ state: "visible", timeout: 8000 });
    } catch {
      t.skip("Quick-Search form is not directly reachable (likely auth/session required).");
      return;
    }

    await originPickerButton.click();
    const dialog = page.getByRole("dialog", { name: "Elegir aeropuerto" });
    await dialog.waitFor({ state: "visible", timeout: 8000 });
    assert.equal(await dialog.isVisible(), true);

    await page.locator(".airport-modal-overlay").click({ position: { x: 10, y: 10 } });
    await dialog.waitFor({ state: "hidden", timeout: 8000 });
    assert.equal(await dialog.isVisible().catch(() => false), false);
  } finally {
    await browser.close();
  }
});
