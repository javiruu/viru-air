import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const I18N_ROOT = path.join(process.cwd(), "src", "i18n");

const FORBIDDEN_PATTERNS = [
  /Ã/,
  /Â/,
  /â€¦/,
];

const DEGRADED_SPANISH_TOKENS = [
  /\bcontrasena\b/i,
  /\bsesion\b/i,
  /\bterminos\b/i,
  /\bpolitica\b/i,
  /\belectronico\b/i,
  /\brecuperacion\b/i,
  /\bsesiónes\b/i,
];

function collectTsFiles(dir: string): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const nextPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...collectTsFiles(nextPath));
      continue;
    }
    if (entry.isFile() && nextPath.endsWith(".ts")) {
      files.push(nextPath);
    }
  }
  return files;
}

test("spanish i18n sources do not contain mojibake or degraded diacritics", () => {
  const files = collectTsFiles(I18N_ROOT);
  const offenders: string[] = [];

  for (const file of files) {
    const content = fs.readFileSync(file, "utf8");
    const isSpanishCarrier =
      /\bsharedEs\b/.test(content) ||
      /\w+Es\s*=\s*\{/.test(content) ||
      file.endsWith(path.join("domains", "public.ts")) ||
      file.endsWith(path.join("domains", "account.ts"));

    if (!isSpanishCarrier) continue;

    for (const pattern of FORBIDDEN_PATTERNS) {
      if (pattern.test(content)) {
        offenders.push(`${file} -> forbidden pattern ${pattern}`);
      }
    }
    for (const pattern of DEGRADED_SPANISH_TOKENS) {
      if (pattern.test(content)) {
        offenders.push(`${file} -> degraded token ${pattern}`);
      }
    }
  }

  assert.deepEqual(offenders, []);
});
