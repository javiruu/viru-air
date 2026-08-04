import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const QUICK_SEARCH_VIEW = path.join(process.cwd(), "src", "modules", "quick-search", "QuickSearchView.tsx");
const QUICK_SEARCH_COPY = path.join(process.cwd(), "src", "modules", "shared", "quickSearchCopy.ts");
const ALERTS_PAGE = path.join(process.cwd(), "src", "modules", "signals", "AlertRulesWorkspace.tsx");

test("quick search save uses save-result without fallback manual create", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
  assert.match(source, /apiFetch<SaveResult>\("\/search\/save-result"/);
  assert.match(source, /response\.created_or_existing === "existing"/);
  assert.doesNotMatch(source, /await apiFetch\("\/watchlist", \{\s*method: "POST"/);
});

test("quick search refresh price reuses watchlist refresh-now flow with rate-limit handling", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
  assert.match(source, /apiFetchWithStatus<\{\s*status: string;/);
  assert.match(source, /`\/watchlist\/\$\{watchId\}\/refresh-now`/);
  assert.match(source, /refreshResponse\.status === 429/);
  assert.match(source, /refreshPriceRateLimited/);
  assert.match(source, /refreshPriceSuccess/);
});

test("quick search save result copies are aligned to created\/existing\/error", () => {
  const source = fs.readFileSync(QUICK_SEARCH_COPY, "utf8");
  assert.match(source, /watchAdded: "Guardado en Watchlist"/);
  assert.match(source, /watchExists: "Ya estaba en Watchlist"/);
  assert.match(source, /watchFailed: "No se pudo guardar"/);
  assert.match(source, /refreshPrice: "Actualizar precio"/);
  assert.match(source, /refreshPriceLoading: "Actualizando precio\.\.\."?/);
  assert.match(source, /refreshPriceRateLimited: "Demasiadas consultas seguidas\. Reintentamos luego\."/);
});

test("alerts includes min_change_pct in create and update payloads and active rows", () => {
  const source = fs.readFileSync(ALERTS_PAGE, "utf8");
  assert.match(source, /min_change_pct: minChangePct \? Number\(minChangePct\) : null/);
  assert.match(source, /min_change_pct: rule\.min_change_pct \?\? null/);
  assert.match(source, /alerts\.row\.minChange/);
});
