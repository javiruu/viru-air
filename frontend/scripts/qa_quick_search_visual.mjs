import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const qaDir = path.join(repoRoot, "docs", "qa");

const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";

const viewports = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet768", width: 768, height: 1024 },
  { name: "mobile375", width: 375, height: 812 },
  { name: "mobile320", width: 320, height: 712 },
];

await mkdir(qaDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const report = {
  generatedAt: new Date().toISOString(),
  baseUrl: BASE_URL,
  snapshots: [],
};

try {
  for (const vp of viewports) {
    const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
    await page.goto(`${BASE_URL}/quick-search`, { waitUntil: "networkidle", timeout: 20000 });

    const fileName = `snapshots_quick-search-${vp.name}.png`;
    const target = path.join(qaDir, fileName);
    const pickerVisible = await page.locator('[data-ui="qs-date-picker-v2"]').first().count();

    let previousHash = null;
    try {
      const previous = await readFile(target);
      previousHash = sha256(previous);
    } catch {
      previousHash = null;
    }

    await page.screenshot({ path: target, fullPage: true });
    const current = await readFile(target);
    const currentHash = sha256(current);

    report.snapshots.push({
      viewport: vp,
      file: path.relative(repoRoot, target),
      pickerV2Visible: pickerVisible > 0,
      previousHash,
      currentHash,
      changed: previousHash ? previousHash !== currentHash : true,
    });

    await page.close();
  }
} finally {
  await browser.close();
}

const reportPath = path.join(qaDir, "quick-search-visual-report.json");
await writeFile(reportPath, JSON.stringify(report, null, 2) + "\n", "utf8");

console.log(`Visual QA report: ${path.relative(repoRoot, reportPath)}`);

function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}
