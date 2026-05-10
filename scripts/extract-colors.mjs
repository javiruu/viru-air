import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(process.cwd(), "frontend/src");
const OUT_DIR = path.resolve(process.cwd(), "docs/color-audit");
const OUT_JSON = path.join(OUT_DIR, "color-inventory.json");

const EXTENSIONS = new Set([".css", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]);

const HEX_RE = /#[0-9a-fA-F]{3,8}\b/g;
const RGB_RE = /rgba?\([^\)]*\)/gi;
const HSL_RE = /hsla?\([^\)]*\)/gi;
const VAR_RE = /--[a-zA-Z0-9_-]+/g;
const COLOR_FUNC_RE = /(color-mix\([^\)]*\)|linear-gradient\([^\)]*\)|radial-gradient\([^\)]*\))/gi;
const TAILWIND_RE = /\b(?:bg|text|border)-(?:white|black|gray-[0-9]{2,3}|neutral-[0-9]{2,3}|stone-[0-9]{2,3}|slate-[0-9]{2,3})\b/g;
const INLINE_STYLE_RE = /style\s*=\s*\{\{[^}]*\b(?:color|background|backgroundColor|borderColor|outlineColor)\b[^}]*\}\}/g;

function walk(dir) {
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...walk(full));
      continue;
    }
    if (EXTENSIONS.has(path.extname(entry.name))) {
      files.push(full);
    }
  }
  return files;
}

function addMatch(map, kind, value, file, line) {
  const key = `${kind}::${value}`;
  if (!map.has(key)) {
    map.set(key, { kind, value, count: 0, files: new Map() });
  }
  const item = map.get(key);
  item.count += 1;
  const perFile = item.files.get(file) ?? [];
  perFile.push(line);
  item.files.set(file, perFile);
}

function lineOfIndex(text, idx) {
  let line = 1;
  for (let i = 0; i < idx; i += 1) {
    if (text.charCodeAt(i) === 10) line += 1;
  }
  return line;
}

function collectRegex(map, text, file, regex, kind) {
  regex.lastIndex = 0;
  let m;
  while ((m = regex.exec(text)) !== null) {
    addMatch(map, kind, m[0], file, lineOfIndex(text, m.index));
    if (m.index === regex.lastIndex) regex.lastIndex += 1;
  }
}

const files = walk(ROOT);
const registry = new Map();

for (const file of files) {
  const text = fs.readFileSync(file, "utf8");
  const rel = path.relative(process.cwd(), file).replace(/\\/g, "/");
  collectRegex(registry, text, rel, HEX_RE, "hex");
  collectRegex(registry, text, rel, RGB_RE, "rgb");
  collectRegex(registry, text, rel, HSL_RE, "hsl");
  collectRegex(registry, text, rel, VAR_RE, "css-var");
  collectRegex(registry, text, rel, COLOR_FUNC_RE, "color-func");
  collectRegex(registry, text, rel, TAILWIND_RE, "utility-class");
  collectRegex(registry, text, rel, INLINE_STYLE_RE, "inline-style");
}

const items = [...registry.values()].map((entry) => ({
  kind: entry.kind,
  value: entry.value,
  count: entry.count,
  files: [...entry.files.entries()].map(([file, lines]) => ({ file, lines }))
}));

items.sort((a, b) => b.count - a.count || a.kind.localeCompare(b.kind) || a.value.localeCompare(b.value));

const summary = items.reduce((acc, it) => {
  acc.totalMatches += it.count;
  acc.uniqueByKind[it.kind] = (acc.uniqueByKind[it.kind] ?? 0) + 1;
  return acc;
}, { scannedRoot: "frontend/src", scannedFiles: files.length, totalMatches: 0, uniqueByKind: {} });

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(OUT_JSON, JSON.stringify({ summary, items }, null, 2));

console.log(`Scanned files: ${summary.scannedFiles}`);
console.log(`Total matches: ${summary.totalMatches}`);
console.log(`Output: ${path.relative(process.cwd(), OUT_JSON).replace(/\\/g, "/")}`);
for (const [kind, count] of Object.entries(summary.uniqueByKind)) {
  console.log(`${kind}: ${count}`);
}
