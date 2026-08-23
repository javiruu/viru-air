import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const watchRowPath = path.join(
  process.cwd(),
  "src",
  "modules",
  "watchlist",
  "components",
  "WatchRow.tsx",
);
const illustrationsPath = path.join(process.cwd(), "public", "illustraciones");
const smartPanelPath = path.join(
  process.cwd(),
  "src",
  "modules",
  "watchlist",
  "components",
  "SmartWatchListPanel.tsx",
);
const screensPath = path.join(process.cwd(), "src", "styles", "screens.css");

test("WatchRow only maps illustrations that exist and leaves unavailable cities neutral", () => {
  const source = fs.readFileSync(watchRowPath, "utf8");
  const mappedIllustrations = [
    ...new Set(
      [...source.matchAll(/art: "([^"]+)"/g)].map(
        ([, illustration]) => `${illustration}.webp`,
      ),
    ),
  ].sort();
  const availableIllustrations = fs
    .readdirSync(illustrationsPath)
    .filter((fileName) => fileName.endsWith(".webp"))
    .sort();

  assert.ok(
    mappedIllustrations.every((illustration) => availableIllustrations.includes(illustration)),
    "every mapped illustration must exist in the public asset directory",
  );
  assert.match(source, /const ticketArt = destination\.art;/);
  assert.match(source, /TRS: \{ label: "Trieste", art: "" \}/);
  assert.match(source, /TSF: \{ label: "Treviso", art: "" \}/);
});

test("Watchlist renders three real ticket rows per page and keeps the compact ticket anatomy", () => {
  const panelSource = fs.readFileSync(smartPanelPath, "utf8");
  const screensSource = fs.readFileSync(screensPath, "utf8");

  assert.match(panelSource, /const WATCHLIST_PAGE_SIZE = 3;/);
  assert.match(panelSource, /smartListItems\.slice\(start, start \+ WATCHLIST_PAGE_SIZE\)/);
  assert.match(screensSource, /\.watch-ticket-row\s*\{[\s\S]*?--watch-ticket-stub-width:\s*26%;/);
  assert.match(screensSource, /\.watch-ticket-row\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0, 74%\) minmax\(190px, 26%\);/);
  assert.match(screensSource, /\.watch-ticket-row\s*\{[\s\S]*?align-items:\s*stretch;/);
  assert.match(screensSource, /\.watch-ticket-row\s*\{[\s\S]*?min-height:\s*0;/);
  assert.match(screensSource, /\.watch-ticket-row\s*\{[\s\S]*?aspect-ratio:\s*1\.72 \/ 1;/);
  assert.match(screensSource, /\.watch-ticket-main\s*\{[\s\S]*?grid-template-rows:\s*28% 12% 18% 24% 18%;/);
  assert.match(screensSource, /\.watch-ticket-route\s*\{[\s\S]*?grid-template-columns:\s*max-content minmax\(1\.45rem, 1fr\) max-content;/);
  assert.doesNotMatch(screensSource, /watch-smart-panel \.watch-ticket-route[\s\S]*?width:\s*48%;/);
  assert.match(screensSource, /\.watch-ticket-pricing\s*\{[\s\S]*?border-top:\s*1px dashed var\(--watch-ticket-line\);/);
  assert.match(screensSource, /\.watch-ticket-stub\s*\{[\s\S]*?border-left:\s*1px dashed var\(--watch-ticket-line\);/);
  assert.match(screensSource, /\.watch-ticket-art\s*\{[\s\S]*?pointer-events:\s*none;/);
  assert.match(panelSource, /WatchRow/);
  assert.match(fs.readFileSync(watchRowPath, "utf8"), /<ArrowRight className="watch-ticket-route-plane"/);
  assert.doesNotMatch(fs.readFileSync(watchRowPath, "utf8"), /type="checkbox"/);
});
