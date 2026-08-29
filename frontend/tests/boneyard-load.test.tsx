import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const LOAD_COMPONENT = path.resolve(TEST_DIR, "../src/modules/shared/BoneyardLoad.tsx");
const CAPTURE_PAGE = path.resolve(TEST_DIR, "../src/app/boneyard-capture/page.tsx");
const REGISTRY = path.resolve(TEST_DIR, "../src/bones/registry.ts");
const LOADING_STYLES = path.resolve(TEST_DIR, "../src/styles/screens.css");

test("Boneyard loading frames retain the generated-bones contract", () => {
  const source = fs.readFileSync(LOAD_COMPONENT, "utf8");

  assert.match(source, /from "boneyard-js\/react"/);
  assert.match(source, /fixture=\{children\}/);
  assert.match(source, /loading/);
  assert.match(source, /name=\{name\}/);
  assert.match(source, /aria-busy="true"/);
  assert.match(source, /BoneyardPanel/);
  assert.match(source, /BoneyardForm/);
  assert.match(source, /BoneyardList/);
  assert.match(source, /BoneyardOverlay/);
});

test("Boneyard honors reduced-motion preferences", () => {
  const styles = fs.readFileSync(LOADING_STYLES, "utf8");

  assert.match(styles, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(styles, /\[data-boneyard-bone="true"\]/);
  assert.match(styles, /animation: none !important/);
});

test("every captured loading state is registered for runtime use", () => {
  const captureSource = fs.readFileSync(CAPTURE_PAGE, "utf8");
  const registry = fs.readFileSync(REGISTRY, "utf8");
  const loadNames = new Set(Array.from(captureSource.matchAll(/"([a-z0-9-]+-load)"/g), ([, name]) => name));

  assert.ok(loadNames.size >= 38, "expected the capture route to cover every named loading state");
  for (const name of loadNames) {
    assert.match(registry, new RegExp(`"${name}"`), `expected generated registry entry for ${name}`);
  }
});
