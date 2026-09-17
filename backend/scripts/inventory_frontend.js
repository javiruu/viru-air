const fs = require('fs');
const path = require('path');

const frontendSrc = path.resolve(__dirname, '../../frontend/src');

function getAllFiles(dir, exts = ['.ts', '.tsx', '.js', '.jsx']) {
  let results = [];
  const list = fs.readdirSync(dir);
  for (const file of list) {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    if (stat.isDirectory()) {
      if (file !== 'node_modules' && file !== '.next') {
        results = results.concat(getAllFiles(fullPath, exts));
      }
    } else if (exts.includes(path.extname(file))) {
      results.push(fullPath);
    }
  }
  return results;
}

const files = getAllFiles(frontendSrc);

const fetchCallSites = [];
const customClientImports = [];
const apiSharedImports = [];
const orvalGeneratedImports = [];
const useQueryCallSites = [];
const useMutationCallSites = [];
const useEffectSites = [];

for (const file of files) {
  const rel = path.relative(frontendSrc, file).replace(/\\/g, '/');
  const content = fs.readFileSync(file, 'utf8');
  const lines = content.split(/\r?\n/);

  lines.forEach((line, idx) => {
    const lineNum = idx + 1;
    if (/\bfetch\s*\(/.test(line)) {
      fetchCallSites.push({ file: rel, line: lineNum, text: line.trim() });
    }
    if (/from\s+['"].*\/customClient['"]/.test(line) || /customClient\s*\(/.test(line)) {
      customClientImports.push({ file: rel, line: lineNum, text: line.trim() });
    }
    if (/from\s+['"].*shared\/api['"]/.test(line)) {
      apiSharedImports.push({ file: rel, line: lineNum, text: line.trim() });
    }
    if (/from\s+['"].*api\/generated/.test(line)) {
      orvalGeneratedImports.push({ file: rel, line: lineNum, text: line.trim() });
    }
    if (/\buseQuery\s*[<\(]/.test(line) || /\buseInfiniteQuery\s*[<\(]/.test(line)) {
      useQueryCallSites.push({ file: rel, line: lineNum, text: line.trim() });
    }
    if (/\buseMutation\s*[<\(]/.test(line)) {
      useMutationCallSites.push({ file: rel, line: lineNum, text: line.trim() });
    }
    if (/\buseEffect\s*\(/.test(line)) {
      // Classification heuristic
      let classification = 'UNKNOWN';
      const context = lines.slice(Math.max(0, idx - 2), Math.min(lines.length, idx + 15)).join('\n');
      if (/fetch|apiFetch|load|refresh|get[A-Z]|async/.test(context) && /set[A-Z]|data|results|error/.test(context)) {
        classification = 'SERVER_STATE';
      } else if (/addEventListener|removeEventListener|window|document|resize|scroll|keydown/.test(context)) {
        classification = 'BROWSER_EFFECT';
      } else if (/subscribe|socket|eventSource|channel/.test(context)) {
        classification = 'SUBSCRIPTION';
      } else if (/focus|ref|scrollIntoView|active|open|close|toggle/.test(context)) {
        classification = 'UI_EFFECT';
      }
      useEffectSites.push({ file: rel, line: lineNum, classification, snippet: line.trim() });
    }
  });
}

const output = {
  total_files_scanned: files.length,
  fetch_call_sites_count: fetchCallSites.length,
  fetch_call_sites: fetchCallSites,
  custom_client_imports_count: customClientImports.length,
  custom_client_imports: customClientImports,
  api_shared_imports_count: apiSharedImports.length,
  api_shared_imports: apiSharedImports,
  orval_generated_imports_count: orvalGeneratedImports.length,
  orval_generated_imports: orvalGeneratedImports,
  use_query_call_sites_count: useQueryCallSites.length,
  use_query_call_sites: useQueryCallSites,
  use_mutation_call_sites_count: useMutationCallSites.length,
  use_mutation_call_sites: useMutationCallSites,
  use_effect_count: useEffectSites.length,
  use_effect_by_class: {
    SERVER_STATE: useEffectSites.filter(e => e.classification === 'SERVER_STATE').length,
    BROWSER_EFFECT: useEffectSites.filter(e => e.classification === 'BROWSER_EFFECT').length,
    UI_EFFECT: useEffectSites.filter(e => e.classification === 'UI_EFFECT').length,
    SUBSCRIPTION: useEffectSites.filter(e => e.classification === 'SUBSCRIPTION').length,
    UNKNOWN: useEffectSites.filter(e => e.classification === 'UNKNOWN').length
  },
  use_effect_sites: useEffectSites
};

fs.writeFileSync(path.resolve(__dirname, '../../docs/migration/frontend-network-inventory.json'), JSON.stringify(output, null, 2));
console.log(JSON.stringify({
  total_files: output.total_files_scanned,
  fetch_calls: output.fetch_call_sites_count,
  custom_client: output.custom_client_imports_count,
  api_shared: output.api_shared_imports_count,
  orval_imports: output.orval_generated_imports_count,
  use_query: output.use_query_call_sites_count,
  use_mutation: output.use_mutation_call_sites_count,
  use_effect: output.use_effect_count,
  use_effect_breakdown: output.use_effect_by_class
}, null, 2));
