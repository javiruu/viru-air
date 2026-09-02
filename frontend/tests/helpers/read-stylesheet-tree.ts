import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const LOCAL_IMPORT = /@import\s+(?:url\()?\s*["']([^"']+\.css)["']\s*\)?\s*;/g;

/**
 * Reads a stylesheet together with its local CSS imports in cascade order.
 *
 * Contract tests use this instead of assuming every selector lives in a
 * monolithic file. External imports are intentionally left untouched.
 */
export function readStylesheetTree(entryPath: string | URL): string {
  const active = new Set<string>();

  function inline(filePath: string): string {
    const absolutePath = path.resolve(filePath);
    if (active.has(absolutePath)) {
      throw new Error(`Circular stylesheet import: ${absolutePath}`);
    }

    active.add(absolutePath);
    const source = fs.readFileSync(absolutePath, "utf8");
    const expanded = source.replace(LOCAL_IMPORT, (statement, importPath: string) => {
      if (/^(?:https?:)?\/\//.test(importPath)) return statement;
      return inline(path.resolve(path.dirname(absolutePath), importPath));
    });
    active.delete(absolutePath);
    return expanded;
  }

  return inline(entryPath instanceof URL ? fileURLToPath(entryPath) : entryPath);
}
