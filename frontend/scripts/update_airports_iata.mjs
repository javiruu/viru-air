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
