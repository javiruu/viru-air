import { readdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const framerMotionDir = path.join(rootDir, "node_modules", "framer-motion", "dist", "es");
const sourceMapCommentPattern = /\r?\n\/\/# sourceMappingURL=.*?\.map\s*$/m;

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = await Promise.all(entries.map(async (entry) => {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      return walk(fullPath);
    }
    return [fullPath];
  }));
  return files.flat();
}

async function main() {
  let dirStats;
  try {
    dirStats = await stat(framerMotionDir);
  } catch {
    return;
  }

  if (!dirStats.isDirectory()) return;

  const files = await walk(framerMotionDir);
  const targetFiles = files.filter((filePath) => filePath.endsWith(".mjs"));
  let updatedFiles = 0;

  await Promise.all(targetFiles.map(async (filePath) => {
    const content = await readFile(filePath, "utf8");
    const nextContent = content.replace(sourceMapCommentPattern, "");
    if (nextContent === content) return;
    await writeFile(filePath, nextContent, "utf8");
    updatedFiles += 1;
  }));

  if (updatedFiles > 0) {
    process.stdout.write(`[strip-framer-motion-sourcemaps] patched ${updatedFiles} files\n`);
  }
}

await main();
