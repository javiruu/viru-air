from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "backend" / "data" / "airports_master.json"
REPORT_PATH = ROOT / "backend" / "data" / "airports_master.report.json"

RYANAIR_AIRPORTS_URLS = (
    "https://www.ryanair.com/api/views/locate/3/airports/en/active",
    "https://www.ryanair.com/api/views/locate/3/airports/es/active",
)
OURAIRPORTS_CSV_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

IATA_RE = re.compile(r"^[A-Z]{3}$")
COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
ALLOWED_TYPES = {"large_airport", "medium_airport", "small_airport"}
TYPE_SCORE = {"large_airport": 3, "medium_airport": 2, "small_airport": 1}
EXCLUDED_CITY_CODES = {"LON", "PAR", "ROM", "MIL", "MOW", "NYC", "TYO"}


def _fetch_json(url: str) -> Any:
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()


def _fetch_text(url: str) -> str:
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/plain,*/*"})
    resp.raise_for_status()
    return resp.text


def _coerce_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not (-90 <= number <= 90 or -180 <= number <= 180):
        return None
    return number


def _parse_ryanair_airports(payload: Any) -> dict[str, dict[str, Any]]:
    airports: dict[str, dict[str, Any]] = {}
    candidates: list[dict[str, Any]] = []

    if isinstance(payload, dict):
        if isinstance(payload.get("airports"), list):
            candidates = [row for row in payload["airports"] if isinstance(row, dict)]
        else:
            for code, row in payload.items():
                if not isinstance(row, dict):
                    continue
                if "iataCode" not in row and "code" not in row:
                    row = {**row, "iataCode": str(code)}
                candidates.append(row)
    elif isinstance(payload, list):
        candidates = [row for row in payload if isinstance(row, dict)]

    for row in candidates:
        iata = str(row.get("iataCode") or row.get("code") or "").strip().upper()
        if not IATA_RE.fullmatch(iata):
            continue
        if iata in EXCLUDED_CITY_CODES:
            continue
        airports[iata] = row
    return airports


def _load_ryanair_airports() -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for url in RYANAIR_AIRPORTS_URLS:
        try:
            payload = _fetch_json(url)
        except requests.RequestException:
            continue
        merged.update(_parse_ryanair_airports(payload))
    if not merged:
        raise RuntimeError("ryanair_airports_unavailable")
    return merged


def _load_ourairports() -> dict[str, dict[str, Any]]:
    raw = _fetch_text(OURAIRPORTS_CSV_URL)
    reader = csv.DictReader(StringIO(raw))
    by_iata: dict[str, dict[str, Any]] = {}
    for row in reader:
        iata = str(row.get("iata_code") or "").strip().upper()
        if not IATA_RE.fullmatch(iata):
            continue
        airport_type = str(row.get("type") or "").strip()
        if airport_type not in ALLOWED_TYPES:
            continue
        country_code = str(row.get("iso_country") or "").strip().upper()
        if not COUNTRY_RE.fullmatch(country_code):
            continue
        lat = _coerce_float(row.get("latitude_deg"))
        lon = _coerce_float(row.get("longitude_deg"))
        if lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            continue

        parsed = {
            "iata": iata,
            "icao": str(row.get("gps_code") or "").strip().upper() or None,
            "name": str(row.get("name") or "").strip() or iata,
            "city": str(row.get("municipality") or "").strip(),
            "country_code": country_code,
            "region": str(row.get("iso_region") or "").strip().upper() or None,
            "timezone": str(row.get("timezone") or "").strip() or None,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "airport_type": airport_type,
        }
        existing = by_iata.get(iata)
        if not existing or TYPE_SCORE[airport_type] > TYPE_SCORE[existing["airport_type"]]:
            by_iata[iata] = parsed
    return by_iata


def main() -> None:
    stations = _load_ryanair_airports()
    reference = _load_ourairports()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    items: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    country_counter: Counter[str] = Counter()

    for iata, station in sorted(stations.items(), key=lambda item: item[0]):
        ref = reference.get(iata)
        if not ref:
            skipped.append({"iata": iata, "reason": "missing_reference"})
            continue

        station_country_code = str(station.get("countryCode") or "").strip().upper()
        if station_country_code and COUNTRY_RE.fullmatch(station_country_code):
            if station_country_code != ref["country_code"]:
                skipped.append({"iata": iata, "reason": "country_mismatch"})
                continue
        country_name = str(station.get("countryName") or station_country_code or ref["country_code"]).strip()
        if not country_name:
            country_name = ref["country_code"]

        items.append(
            {
                "iata": iata,
                "icao": ref["icao"],
                "name": ref["name"],
                "city": ref["city"] or str(station.get("name") or station.get("cityCode") or "").strip(),
                "country": country_name,
                "region": ref["region"],
                "latitude": ref["latitude"],
                "longitude": ref["longitude"],
                "timezone": ref["timezone"],
                "airport_type": ref["airport_type"],
                "is_primary": ref["airport_type"] == "large_airport",
                "source": f"ryanair_airports+ourairports:{generated_at}",
            }
        )
        country_counter.update([ref["country_code"]])

    items.sort(key=lambda row: (str(row["region"] or ""), str(row["city"]), str(row["name"]), str(row["iata"])))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(items, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    REPORT_PATH.write_text(
        json.dumps(
            {
                "generated_at_utc": generated_at,
                "source": "ryanair_airports+ourairports",
                "total_airports": len(items),
                "countries_total": len(country_counter),
                "countries": dict(sorted(country_counter.items())),
                "skipped": skipped,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(items)} airports to {OUT_PATH}")
    print(f"wrote report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
