import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const QUICK_SEARCH_VIEW = path.join(process.cwd(), "src", "modules", "quick-search", "QuickSearchView.tsx");

test("quick-search requests monthly calendar hints from backend", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
  assert.match(source, /\/search\/quick\/calendar-hints/);
  assert.match(source, /setCalendarHintsByKey/);
  assert.match(source, /calendarHintsRequestKey/);
  assert.match(source, /aggregation_mode:\s*calendarHintAggregationMode/);
  assert.match(source, /bucket_mode:\s*calendarHintBucketMode/);
  assert.match(source, /guideline_thresholds:\s*calendarHintBucketMode === "guidelines" \? calendarHintGuidelineThresholds : undefined/);
  assert.match(source, /origin_iata:\s*originCountryOnly/);
  assert.match(source, /destination_iata:\s*destinationCountryOnly/);
});

test("quick-search long-running requests bypass the local Next proxy", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
  assert.match(source, /LONG_RUNNING_API_BASE/);
  assert.match(source, /\/search\/quick\/calendar-hints[\s\S]*?apiBase:\s*LONG_RUNNING_API_BASE/);
  assert.match(source, /apiFetchWithStatus<SearchResponseRaw>\("\/search\/quick"[\s\S]*?apiBase:\s*LONG_RUNNING_API_BASE/);
});

test("outbound date picker is wired with hints props and visible-month callback", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
  assert.match(source, /name="travel_date"/);
  assert.match(source, /dayHintsByIso=\{calendarHintsActive\?\.dayHintsByIso \|\| \{\}\}/);
  assert.match(source, /hintsLoading=\{calendarHintsLoadingKey === calendarHintsRequestKey\}/);
  assert.match(source, /showCountryEstimateBadge=\{canRequestCalendarHints && hasCountryScopeForCalendarHints\}/);
  assert.match(source, /hintScopeMode=\{calendarHintsActive\?\.scopeMode \|\| calendarHintsScopeMode\}/);
  assert.match(source, /onVisibleMonthChange=\{setCalendarVisibleMonth\}/);
});

test("outbound date picker cannot submit days before today", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
  assert.match(source, /function currentDateIso\(\): string/);
  assert.match(source, /const minTravelDate = useMemo\(\(\) => currentDateIso\(\), \[\]\)/);
  assert.match(source, /name="travel_date"[\s\S]*?min=\{minTravelDate\}/);
});

test("quick-search submit is locked before async request preparation", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
  assert.match(source, /const searchSubmitInFlightRef = useRef\(false\)/);
  assert.match(source, /if \(searchSubmitInFlightRef\.current\) return/);
  assert.match(source, /searchSubmitInFlightRef\.current = true/);
  assert.match(source, /disabled=\{!isReady \|\| !routeInputsValid \|\| isSubmitting \|\| isLoading\}/);
});

test("quick-search dynamic chunks retry transient Fast Refresh load failures", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
  assert.match(source, /function isTransientChunkLoadError\(error: unknown\): boolean/);
  assert.match(source, /function retryQuickSearchChunk<T>\(loader: \(\) => Promise<T>\): Promise<T>/);
  assert.match(source, /retryQuickSearchChunk\(\(\) =>\s*import\("@\/modules\/quick-search\/components\/QuickSearchResultsList"\)/);
});

test("calendar hints failures are treated as non-fatal and cached as empty state", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
  assert.match(source, /"calendar_hints_failed"/);
  assert.match(source, /"calendar_hints_exception"/);
  assert.match(source, /"calendar_hints_return_failed"/);
  assert.match(source, /"calendar_hints_return_exception"/);
  assert.match(source, /buildEmptyCalendarHintsCacheEntry\(calendarHintsScopeMode\)/);
});
