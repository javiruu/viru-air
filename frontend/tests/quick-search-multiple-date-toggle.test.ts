import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";
import { readStylesheetTree } from "./helpers/read-stylesheet-tree";

test("multiple-date toggle uses the orange accent only while active", () => {
  const css = readStylesheetTree(path.join(process.cwd(), "src", "styles", "screens.css"));

  assert.match(css, /\.qs-date-nav--multiple\.is-active\s*\{[^}]*background:\s*var\(--accent\)/s);
  assert.match(css, /\.qs-date-nav--multiple\.is-active\s*\{[^}]*color:\s*var\(--accent-ink\)/s);
  assert.match(css, /:root\[data-theme="dark"\]\s+\.qs-date-nav--multiple\.is-active\s*\{[^}]*background:\s*var\(--accent\)/s);
});
