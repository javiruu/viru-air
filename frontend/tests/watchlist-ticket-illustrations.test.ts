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

test("WatchRow covers every ticket illustration and has a route-art fallback", () => {
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

  assert.deepEqual(mappedIllustrations, availableIllustrations);
  assert.match(source, /destination\.art \|\| origin\.art/);
  assert.match(source, /TRS: \{ label: "Trieste", art: "" \}/);
});
