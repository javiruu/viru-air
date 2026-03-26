# Quick-Search Airports IATA Dataset Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate a full IATA airport dataset into /quick-search for robust origin/destination selection and country-based listings.

**Architecture:** Add a versioned JSON dataset generated from OurAirports via a local script, then index it in memory in `page.tsx` for country lists, IATA lookups, and modal search filtering. Keep UI layout unchanged; only data sources and validation logic are updated.

**Tech Stack:** Next.js (App Router), React, TypeScript, Node (ESM script), global CSS.

---

### Task 1: Add dataset generation script

**Files:**
- Create: `frontend/scripts/update_airports_iata.mjs`

**Step 1: Write the file**
```js
// frontend/scripts/update_airports_iata.mjs
import fs from "node:fs";
import path from "node:path";
import https from "node:https";

const OURAIRPORTS_CSV_URL =
  "https://davidmegginson.github.io/ourairports-data/airports.csv";

const OUT_PATH = path.resolve(
  process.cwd(),
  "frontend/src/data/airports_iata.min.json"
);

function fetchText(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, (res) => {
        if (res.statusCode !== 200) {
          reject(new Error(`HTTP ${res.statusCode} for ${url}`));
          res.resume();
          return;
        }
        res.setEncoding("utf8");
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => resolve(data));
      })
      .on("error", reject);
  });
}

// CSV parser minimo (maneja comillas dobles y comas)
function parseCsv(csv) {
  const lines = csv.split(/\r?\n/).filter(Boolean);
  const header = splitCsvLine(lines[0]);
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = splitCsvLine(lines[i]);
    if (cols.length !== header.length) continue;
    const obj = {};
    for (let j = 0; j < header.length; j++) obj[header[j]] = cols[j];
    rows.push(obj);
  }
  return rows;
}

function splitCsvLine(line) {
  const out = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"' && line[i + 1] === '"') {
      cur += '"';
      i++;
      continue;
    }
    if (ch === '"') {
      inQuotes = !inQuotes;
      continue;
    }
    if (ch === "," && !inQuotes) {
      out.push(cur);
      cur = "";
      continue;
    }
    cur += ch;
  }
  out.push(cur);
  return out;
}

const TYPE_SCORE = {
  large_airport: 3,
  medium_airport: 2,
  small_airport: 1,
};

function pickBetter(a, b) {
  const sa = TYPE_SCORE[a.type] ?? 0;
  const sb = TYPE_SCORE[b.type] ?? 0;
  if (sb > sa) return b;
  return a;
}

(async function main() {
  const csv = await fetchText(OURAIRPORTS_CSV_URL);
  const rows = parseCsv(csv);

  const map = new Map(); // iata -> entry
  for (const r of rows) {
    const iata = (r.iata_code || "").trim().toUpperCase();
    if (!iata || iata.length !== 3) continue;

    const entry = {
      iata,
      name: (r.name || "").trim(),
      municipality: (r.municipality || "").trim(),
      country_code: (r.iso_country || "").trim().toUpperCase(),
      iso_region: (r.iso_region || "").trim(),
      type: (r.type || "").trim(),
    };

    const prev = map.get(iata);
    if (!prev) map.set(iata, entry);
    else map.set(iata, pickBetter(prev, entry));
  }

  const list = Array.from(map.values()).sort((a, b) => {
    if (a.country_code !== b.country_code)
      return a.country_code.localeCompare(b.country_code);
    if (a.municipality !== b.municipality)
      return a.municipality.localeCompare(b.municipality);
    return a.name.localeCompare(b.name);
  });

  fs.mkdirSync(path.dirname(OUT_PATH), { recursive: true });
  fs.writeFileSync(OUT_PATH, JSON.stringify(list), "utf8");
  process.stdout.write(
    `Wrote ${list.length} airports with IATA to ${OUT_PATH}\n`
  );
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
```

**Step 2: Commit**
```bash
git add frontend/scripts/update_airports_iata.mjs
git commit -m "chore: add airports IATA dataset generator"
```

---

### Task 2: Generate and version the dataset

**Files:**
- Create: `frontend/src/data/airports_iata.min.json`

**Step 1: Run the generator**
Run: `npm run update:airports`
Expected: `Wrote <N> airports with IATA to .../frontend/src/data/airports_iata.min.json`

**Step 2: Commit**
```bash
git add frontend/src/data/airports_iata.min.json
git commit -m "chore: add airports IATA dataset"
```

---

### Task 3: Wire dataset into quick-search UI

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/app/(private)/quick-search/page.tsx`

**Step 1: Add npm script**
Edit `frontend/package.json` scripts:
```json
"update:airports": "node ./frontend/scripts/update_airports_iata.mjs"
```

**Step 2: Import dataset**
At top of `page.tsx` add:
```ts
import airportsIata from "@/data/airports_iata.min.json";
```

**Step 3: Build indexes**
Near top-level (module scope) add:
```ts
const AIRPORTS = airportsIata as Array<{
  iata: string;
  name: string;
  municipality: string;
  country_code: string;
  iso_region: string;
  type: string;
}>;

const airportsByCountry = new Map<string, typeof AIRPORTS>();
const airportsByIata = new Map<string, (typeof AIRPORTS)[number]>();

for (const a of AIRPORTS) {
  airportsByIata.set(a.iata, a);
  const key = a.country_code || "";
  const list = airportsByCountry.get(key) || [];
  list.push(a);
  airportsByCountry.set(key, list);
}
```

**Step 4: Modal list by country**
Replace modal list source with:
```ts
const countryAirports = airportsByCountry.get(selectedCountryCode) || [];
```
Render each item with:
- label: `municipality || name`
- code: `iata`

**Step 5: Modal search filtering**
Replace filter with:
```ts
const q = query.trim().toLowerCase();
const filtered = countryAirports.filter((a) => {
  if (!q) return true;
  if (a.iata.toLowerCase().startsWith(q)) return true;
  if (a.name.toLowerCase().includes(q)) return true;
  if (a.municipality.toLowerCase().includes(q)) return true;
  return false;
});
const visible = filtered.length > 200 ? filtered.slice(0, 200) : filtered;
```

**Step 6: IATA validation**
Update validation condition to:
```ts
const code = value.trim().toUpperCase();
const isValid = code.length === 3 && airportsByIata.has(code);
```

**Step 7: Commit**
```bash
git add frontend/package.json frontend/src/app/(private)/quick-search/page.tsx
git commit -m "feat: use global airports IATA dataset in quick-search"
```

---

### Task 4: Manual QA (no automated tests)

**Files:**
- None

**Step 1: Dataset generation**
Run: `npm run update:airports`
Expected: JSON file generated with thousands of entries.

**Step 2: UI checks**
- `/quick-search` -> modal "Pais de origen" -> ES -> search "Sevilla" -> see `SVQ`.
- `/quick-search` -> IT -> search "Rome" or "Roma" -> see `FCO` / `CIA`.
- Input `MAD` -> no invalid code error.

**Step 3: Commit QA note**
No commit required (manual QA only).

---

**Skills referenced:** @brainstorming, @writing-plans
