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

test("WatchRow resolves city names dynamically and prefers an available origin illustration", () => {
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
  assert.match(source, /getAirportMeta\(code\)\?\.city/);
  assert.match(source, /const ticketArt = origin\.art \|\| destination\.art;/);
  assert.match(source, /TRS: \{ label: "Trieste", art: "" \}/);
  assert.match(source, /TSF: \{ label: "Treviso", art: "" \}/);
});

test("WatchRow omits the active-status pill while preserving other lifecycle states", () => {
  const source = fs.readFileSync(watchRowPath, "utf8");

  assert.match(source, /const showWatchStatus = watch\.status !== "active";/);
  assert.match(source, /\{showWatchStatus \? <span className=\{`status-pill \$\{watchStatus\.tone\}`\}>\{watchStatus\.label\}<\/span> : null\}/);
});

test("Watchlist ticket preserves the desktop ticket anatomy inside its narrow route column", () => {
  const panelSource = fs.readFileSync(smartPanelPath, "utf8");
  const screensSource = fs.readFileSync(screensPath, "utf8");

  assert.match(panelSource, /const WATCHLIST_PAGE_SIZE = 3;/);
  assert.match(panelSource, /smartListItems\.slice\(start, start \+ WATCHLIST_PAGE_SIZE\)/);
  assert.match(screensSource, /\.watch-ticket-row\s*\{[\s\S]*?--watch-ticket-stub-width:\s*25\.25%;/);
  assert.match(screensSource, /\.watch-ticket-row\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0, 74\.75%\) minmax\(0, 25\.25%\);/);
  assert.doesNotMatch(screensSource, /grid-template-columns:\s*minmax\(0, 74%\) minmax\(190px, 26%\);/);
  assert.doesNotMatch(screensSource, /html\s*\{\s*zoom:\s*75%;/);
  assert.match(screensSource, /\.watch-ticket-row\s*\{[\s\S]*?align-items:\s*stretch;/);
  assert.match(screensSource, /\.watch-ticket-row\s*\{[\s\S]*?min-height:\s*0;/);
  assert.match(screensSource, /\.watch-ticket-row\s*\{[\s\S]*?aspect-ratio:\s*1\.72 \/ 1;/);
  assert.match(screensSource, /\.watch-ticket-main\s*\{[\s\S]*?grid-template-rows:\s*30% 12% 17% 25% 16%;/);
  assert.match(screensSource, /\.watch-ticket-route\s*\{[\s\S]*?grid-template-columns:\s*max-content minmax\(1\.45rem, 1fr\) max-content;/);
  assert.doesNotMatch(screensSource, /watch-smart-panel \.watch-ticket-route[\s\S]*?width:\s*48%;/);
  assert.match(screensSource, /\.watch-ticket-pricing\s*\{[\s\S]*?border-top:\s*1px dashed var\(--watch-ticket-line\);/);
  assert.match(screensSource, /\.watch-ticket-stub\s*\{[\s\S]*?grid-template-rows:\s*59% 41%;/);
  assert.match(screensSource, /\.watch-ticket-stub\s*\{[\s\S]*?border-left:\s*0;/);
  assert.match(screensSource, /\.watch-smart-panel\s*\{[\s\S]*?container:\s*watch-smart-panel \/ inline-size;/);
  assert.match(screensSource, /@container watch-smart-panel \(max-width:\s*32rem\)/);
  assert.match(screensSource, /\.watch-ticket-art\s*\{[\s\S]*?pointer-events:\s*none;/);
  assert.match(panelSource, /WatchRow/);
  assert.match(fs.readFileSync(watchRowPath, "utf8"), /<ArrowRight className="watch-ticket-route-plane"/);
  assert.doesNotMatch(fs.readFileSync(watchRowPath, "utf8"), /type="checkbox"/);
});
