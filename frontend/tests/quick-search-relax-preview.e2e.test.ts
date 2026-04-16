import assert from "node:assert/strict";
import test from "node:test";

import { chromium } from "playwright";

const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";

test("quick-search relax filters preview supports cancel and confirm", async (t) => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });

  try {
    try {
      await page.goto(`${BASE_URL}/quick-search`, { waitUntil: "domcontentloaded", timeout: 15000 });
    } catch {
      t.skip(`Quick-Search not reachable at ${BASE_URL}. Start frontend and retry.`);
      return;
    }

    const originInput = page.locator('input[name="origin_iata"]');
    const destinationInput = page.locator('input[name="destination_iata"]');
    const datePicker = page.locator('[data-ui="qs-date-picker-v2"]').first();

    try {
      await originInput.waitFor({ state: "visible", timeout: 8000 });
      await destinationInput.waitFor({ state: "visible", timeout: 8000 });
      await datePicker.waitFor({ state: "visible", timeout: 8000 });
    } catch {
      t.skip("Quick-Search form is not directly reachable (likely auth/session required).");
      return;
    }

    await originInput.fill("MAD");
    await destinationInput.fill("DUB");
    await datePicker.locator(".qs-date-trigger").click();
    await page.locator(".qs-date-popover .qs-date-day:not(.is-disabled):not(.is-outside)").nth(10).click();
    await page.getByRole("button", { name: "Buscar" }).click();

    const relaxButton = page.getByRole("button", { name: "Relajar filtros" }).first();
    try {
      await relaxButton.waitFor({ state: "visible", timeout: 12000 });
    } catch {
      t.skip("Relax flow requires empty-state response for this environment.");
      return;
    }

    await relaxButton.click();
    await expectVisible(page, "Cambios propuestos");

    await page.getByRole("button", { name: "Cancelar" }).click();
    await expectHidden(page, "Cambios propuestos");

    await relaxButton.click();
    await page.getByRole("button", { name: "Aplicar cambios y buscar" }).click();
    await expectHidden(page, "Cambios propuestos");
  } finally {
    await browser.close();
  }
});

async function expectVisible(page: import("playwright").Page, text: string) {
  const locator = page.getByText(text, { exact: false }).first();
  await locator.waitFor({ state: "visible", timeout: 8000 });
  assert.equal(await locator.isVisible(), true);
}

async function expectHidden(page: import("playwright").Page, text: string) {
  const locator = page.getByText(text, { exact: false }).first();
  await locator.waitFor({ state: "hidden", timeout: 8000 });
  assert.equal(await locator.isVisible().catch(() => false), false);
}
