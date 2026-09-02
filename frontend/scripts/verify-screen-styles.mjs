import fs from "node:fs";
import path from "node:path";
import postcss from "postcss";

const projectRoot = process.cwd();
const entryPath = path.join(projectRoot, "src", "styles", "screens.css");
const screenRoot = path.join(projectRoot, "src", "styles", "screens");
const importPattern = /@import\s+["']([^"']+\.css)["']\s*;/g;
const maximumModuleLines = 3_000;

const manifest = fs.readFileSync(entryPath, "utf8");
const manifestRemainder = manifest
  .replace(/\/\*[\s\S]*?\*\//g, "")
  .replace(importPattern, "")
  .trim();

if (manifestRemainder) {
  throw new Error("screens.css must remain an import-only compatibility entrypoint.");
}

const imports = Array.from(manifest.matchAll(importPattern), (match) => match[1]);
if (imports.length === 0) {
  throw new Error("screens.css does not import any screen modules.");
}

if (new Set(imports).size !== imports.length) {
  throw new Error("screens.css contains duplicate module imports.");
}

let totalRules = 0;
let totalLines = 0;

for (const importPath of imports) {
  const absolutePath = path.resolve(path.dirname(entryPath), importPath);
  const relativeToRoot = path.relative(screenRoot, absolutePath);
  if (relativeToRoot.startsWith("..") || path.isAbsolute(relativeToRoot)) {
    throw new Error(`Screen module escapes src/styles/screens: ${importPath}`);
  }
  if (!fs.existsSync(absolutePath)) {
    throw new Error(`Missing screen module: ${importPath}`);
  }

  const source = fs.readFileSync(absolutePath, "utf8");
  const lineCount = source.split(/\r?\n/).length;
  if (lineCount > maximumModuleLines) {
    throw new Error(`${importPath} has ${lineCount} lines; split it below ${maximumModuleLines}.`);
  }

  const root = postcss.parse(source, { from: absolutePath });
  root.walkRules(() => {
    totalRules += 1;
  });
  totalLines += lineCount;
}

const diskModules = [];
for (const directoryEntry of fs.readdirSync(screenRoot, { recursive: true, withFileTypes: true })) {
  if (!directoryEntry.isFile() || !directoryEntry.name.endsWith(".css")) continue;
  diskModules.push(path.join(directoryEntry.parentPath, directoryEntry.name));
}

const importedModules = new Set(imports.map((importPath) => path.resolve(path.dirname(entryPath), importPath)));
const orphanModules = diskModules.filter((filePath) => !importedModules.has(path.resolve(filePath)));
if (orphanModules.length > 0) {
  throw new Error(`Unreferenced screen modules: ${orphanModules.join(", ")}`);
}

console.log(`Screen styles valid: ${imports.length} modules, ${totalLines} lines, ${totalRules} rules.`);
