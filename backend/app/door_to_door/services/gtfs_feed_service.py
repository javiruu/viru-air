"""GTFS feed service: download, cache, parse, and query GTFS static feeds.

MVP scope:
- Download .zip from declared feed URLs
- Cache on disk with configurable TTL
- Validate minimum required files
- Parse stops, routes, trips, stop_times, and calendar/calendar_dates
- Query nearby stops by lat/lng
- Query trips for a given date/time between two stops
"""

import csv
import hashlib
import io
import json
import logging
import os
import time
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("app.door_to_door.gtfs")

# ---------------------------------------------------------------------------
# Config / env defaults
# ---------------------------------------------------------------------------

DEFAULT_CACHE_DIR = Path(os.getenv("DOOR_TO_DOOR_GTFS_CACHE_DIR", ".gtfs_cache"))
DEFAULT_CACHE_TTL = int(os.getenv("DOOR_TO_DOOR_GTFS_CACHE_TTL_SECONDS", "86400"))  # 24 h
DEFAULT_MAX_WALK_RADIUS = int(os.getenv("DOOR_TO_DOOR_GTFS_MAX_WALK_RADIUS_METERS", "2000"))
DEFAULT_MAX_RESULTS = int(os.getenv("DOOR_TO_DOOR_GTFS_MAX_RESULTS", "3"))
DEFAULT_DOWNLOAD_TIMEOUT = 20.0
_REQUIRED_FILES = {"agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt"}

# Route type constants (GTFS standard)
_ROUTE_TYPE_NAMES: dict[int, str] = {
    0: "tram",
    1: "metro",
    2: "train",
    3: "bus",
    4: "ferry",
    5: "cable_tram",
    6: "aerial_lift",
    7: "funicular",
    11: "trolleybus",
    12: "monorail",
    800: "trolleybus",
    900: "tram",
    1000: "boat",
}


# ---------------------------------------------------------------------------
# Feed descriptor
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GtfsFeedDescriptor:
    id: str
    name: str
    region: str
    url: str
    source_type: str = "open_data"
    license_url: str | None = None
    attribution: str | None = None


def load_feed_descriptors() -> list[GtfsFeedDescriptor]:
    """Load feed descriptors from DOOR_TO_DOOR_GTFS_FEEDS_JSON env or return empty."""
    raw = os.getenv("DOOR_TO_DOOR_GTFS_FEEDS_JSON", "")
    if not raw.strip():
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("gtfs_feed_descriptors_invalid_json")
        return []
    descriptors: list[GtfsFeedDescriptor] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if not item.get("id") or not item.get("url"):
            continue
        descriptors.append(
            GtfsFeedDescriptor(
                id=item["id"],
                name=item.get("name", item["id"]),
                region=item.get("region", ""),
                url=item["url"],
                source_type=item.get("source_type", "open_data"),
                license_url=item.get("license_url"),
                attribution=item.get("attribution"),
            )
        )
    return descriptors


# ---------------------------------------------------------------------------
# In-memory parsed GTFS feed
# ---------------------------------------------------------------------------

@dataclass
class GtfsStop:
    stop_id: str
    name: str
    lat: float
    lon: float


@dataclass
class GtfsRoute:
    route_id: str
    agency_id: str
    short_name: str
    long_name: str
    route_type: int


@dataclass
class GtfsTrip:
    trip_id: str
    route_id: str
    service_id: str
    headsign: str


@dataclass
class GtfsStopTime:
    trip_id: str
    stop_id: str
    arrival_seconds: int  # seconds from midnight
    departure_seconds: int
    stop_sequence: int


@dataclass
class GtfsAgency:
    agency_id: str
    name: str


@dataclass
class ParsedGtfsFeed:
    feed_id: str
    downloaded_at: float  # epoch seconds
    agencies: dict[str, GtfsAgency] = field(default_factory=dict)
    stops: dict[str, GtfsStop] = field(default_factory=dict)
    routes: dict[str, GtfsRoute] = field(default_factory=dict)
    trips: dict[str, GtfsTrip] = field(default_factory=dict)
    stop_times: dict[str, list[GtfsStopTime]] = field(default_factory=dict)  # trip_id -> stop_times (sorted)
    calendar: dict[str, set[date]] = field(default_factory=dict)  # service_id -> active dates
    calendar_dates: dict[str, dict[date, int]] = field(default_factory=dict)  # service_id -> {date: exception_type}


# ---------------------------------------------------------------------------
# Cached transit leg
# ---------------------------------------------------------------------------

@dataclass
class GtfsTransitLeg:
    """A single transit trip result from origin stop to destination stop."""
    feed_id: str
    agency_name: str
    route_name: str
    mode: str  # "bus", "train", "metro", "tram", etc.
    departure_at: datetime
    arrival_at: datetime
    duration_minutes: int
    from_stop_name: str
    to_stop_name: str
    from_stop_id: str
    to_stop_id: str


# ---------------------------------------------------------------------------
# GtfsFeedService
# ---------------------------------------------------------------------------

class GtfsFeedService:
    """Manage GTFS feed lifecycle: download, cache, parse, query."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        cache_ttl_seconds: int | None = None,
        max_walk_radius_meters: int | None = None,
        max_results: int | None = None,
    ) -> None:
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_ttl = cache_ttl_seconds if cache_ttl_seconds is not None else DEFAULT_CACHE_TTL
        self.max_walk_radius = max_walk_radius_meters if max_walk_radius_meters is not None else DEFAULT_MAX_WALK_RADIUS
        self.max_results = max_results if max_results is not None else DEFAULT_MAX_RESULTS
        self._feeds: dict[str, ParsedGtfsFeed] = {}
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ---- public API ----

    def load_feed(self, descriptor: GtfsFeedDescriptor) -> ParsedGtfsFeed | None:
        """Get a parsed feed, downloading/caching if needed. Returns None on failure."""
        if descriptor.id in self._feeds:
            feed = self._feeds[descriptor.id]
            if (time.time() - feed.downloaded_at) < self.cache_ttl:
                return feed

        cached_path = self._cache_path(descriptor)
        if cached_path.exists():
            stat = cached_path.stat()
            age = time.time() - stat.st_mtime
            if age < self.cache_ttl:
                feed = self._parse_feed(cached_path, descriptor.id)
                if feed is not None:
                    self._feeds[descriptor.id] = feed
                    return feed

        try:
            raw_bytes = self._download(descriptor.url)
        except Exception:
            logger.warning("gtfs_download_failed", extra={"feed_id": descriptor.id, "url": descriptor.url})
            # Try stale cache
            if cached_path.exists():
                feed = self._parse_feed(cached_path, descriptor.id)
                if feed is not None:
                    feed.downloaded_at = time.time()  # mark as stale but usable
                    self._feeds[descriptor.id] = feed
                    return feed
            return None

        # Validate zip
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                names = set(zf.namelist())
                missing = _REQUIRED_FILES - names
                if missing:
                    logger.warning("gtfs_missing_required_files", extra={"feed_id": descriptor.id, "missing": list(missing)})
                    return None
        except zipfile.BadZipFile:
            logger.warning("gtfs_bad_zip", extra={"feed_id": descriptor.id})
            return None

        cached_path.write_bytes(raw_bytes)
        feed = self._parse_feed(cached_path, descriptor.id)
        if feed is not None:
            self._feeds[descriptor.id] = feed
        return feed

    def find_nearby_stops(self, feed_id: str, lat: float, lng: float) -> list[GtfsStop]:
        """Find stops within max_walk_radius of the given coordinates, sorted nearest first."""
        feed = self._feeds.get(feed_id)
        if feed is None:
            return []
        stops: list[tuple[float, GtfsStop]] = []
        for stop in feed.stops.values():
            dist = _haversine_meters(lat, lng, stop.lat, stop.lon)
            if dist <= self.max_walk_radius:
                stops.append((dist, stop))
        stops.sort(key=lambda item: item[0])
        return [s for _, s in stops[: self.max_results * 2]]

    def find_trips_between(
        self,
        feed_id: str,
        from_stop_id: str,
        to_stop_id: str,
        target_date: date,
        earliest_departure: datetime | None = None,
        latest_arrival: datetime | None = None,
    ) -> list[GtfsTransitLeg]:
        """Find direct trips from from_stop_id to to_stop_id on target_date."""
        feed = self._feeds.get(feed_id)
        if feed is None:
            return []

        active_services = self._active_services(feed, target_date)
        if not active_services:
            return []

        from_times: dict[str, int] = {}  # trip_id -> departure_seconds
        to_times: dict[str, int] = {}    # trip_id -> arrival_seconds

        # Collect departure times at from_stop
        for trip_id, st_list in feed.stop_times.items():
            for st in st_list:
                if st.stop_id == from_stop_id:
                    from_times[trip_id] = st.departure_seconds
                    break

        # Collect arrival times at to_stop
        for trip_id, st_list in feed.stop_times.items():
            for st in st_list:
                if st.stop_id == to_stop_id:
                    to_times[trip_id] = st.arrival_seconds

        results: list[GtfsTransitLeg] = []
        earliest_seconds: int | None = None
        latest_seconds: int | None = None

        if earliest_departure is not None:
            earliest_seconds = earliest_departure.hour * 3600 + earliest_departure.minute * 60
        if latest_arrival is not None:
            latest_seconds = latest_arrival.hour * 3600 + latest_arrival.minute * 60

        for trip_id, dep_sec in from_times.items():
            arr_sec = to_times.get(trip_id)
            if arr_sec is None or arr_sec <= dep_sec:
                continue
            trip = feed.trips.get(trip_id)
            if trip is None:
                continue
            if trip.service_id not in active_services:
                continue

            # Time window filter
            if earliest_seconds is not None and dep_sec < earliest_seconds:
                continue
            if latest_seconds is not None and arr_sec > latest_seconds:
                continue

            route = feed.routes.get(trip.route_id)
            if route is None:
                continue
            agency = feed.agencies.get(route.agency_id)
            mode = _route_type_name(route.route_type)
            duration = arr_sec - dep_sec

            dep_dt = datetime(
                target_date.year, target_date.month, target_date.day,
                dep_sec // 3600, (dep_sec % 3600) // 60, dep_sec % 60,
                tzinfo=timezone.utc,
            )
            arr_dt = datetime(
                target_date.year, target_date.month, target_date.day,
                arr_sec // 3600, (arr_sec % 3600) // 60, arr_sec % 60,
                tzinfo=timezone.utc,
            )

            from_stop = feed.stops.get(from_stop_id)
            to_stop = feed.stops.get(to_stop_id)

            results.append(
                GtfsTransitLeg(
                    feed_id=feed_id,
                    agency_name=agency.name if agency else route.agency_id,
                    route_name=route.short_name or route.long_name or route.route_id,
                    mode=mode,
                    departure_at=dep_dt,
                    arrival_at=arr_dt,
                    duration_minutes=int(duration / 60),
                    from_stop_name=from_stop.name if from_stop else from_stop_id,
                    to_stop_name=to_stop.name if to_stop else to_stop_id,
                    from_stop_id=from_stop_id,
                    to_stop_id=to_stop_id,
                )
            )

        # Sort by departure time
        results.sort(key=lambda leg: leg.departure_at)
        return results[: self.max_results]

    # ---- internal ----

    def _cache_path(self, descriptor: GtfsFeedDescriptor) -> Path:
        name_hash = hashlib.sha256(descriptor.id.encode()).hexdigest()[:16]
        return self.cache_dir / f"{descriptor.id}_{name_hash}.zip"

    @staticmethod
    def _download(url: str) -> bytes:
        resp = httpx.get(url, timeout=DEFAULT_DOWNLOAD_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        return resp.content

    @staticmethod
    def _parse_feed(path: Path, feed_id: str) -> ParsedGtfsFeed | None:
        try:
            with zipfile.ZipFile(path, "r") as zf:
                agencies = _parse_csv(zf, "agency.txt", _parse_agency)
                stops = _parse_csv(zf, "stops.txt", _parse_stop)
                routes = _parse_csv(zf, "routes.txt", _parse_route)
                trips = _parse_csv(zf, "trips.txt", _parse_trip)
                stop_times_list = _parse_stop_times(zf)
                calendar: dict[str, set[date]] = {}
                calendar_dates: dict[str, dict[date, int]] = {}
                if "calendar.txt" in zf.namelist():
                    calendar = _parse_calendar(zf)
                if "calendar_dates.txt" in zf.namelist():
                    calendar_dates = _parse_calendar_dates(zf)

            # Index stop_times by trip_id (sorted by stop_sequence)
            stop_times: dict[str, list[GtfsStopTime]] = {}
            for st in stop_times_list:
                stop_times.setdefault(st.trip_id, []).append(st)
            for st_list in stop_times.values():
                st_list.sort(key=lambda st: st.stop_sequence)

            return ParsedGtfsFeed(
                feed_id=feed_id,
                downloaded_at=time.time(),
                agencies=agencies,
                stops=stops,
                routes=routes,
                trips=trips,
                stop_times=stop_times,
                calendar=calendar,
                calendar_dates=calendar_dates,
            )
        except Exception:
            logger.exception("gtfs_parse_failed", extra={"feed_id": feed_id})
            return None

    @staticmethod
    def _active_services(feed: ParsedGtfsFeed, target_date: date) -> set[str]:
        """Determine which service_ids are active on target_date."""
        active: set[str] = set()

        # calendar.txt
        day_name = target_date.strftime("%A").lower()
        for sid, dates in feed.calendar.items():
            if target_date in dates:
                active.add(sid)

        # calendar_dates.txt (exceptions override)
        if sid in feed.calendar_dates:
            exc = feed.calendar_dates[sid].get(target_date)
            if exc == 2:  # service removed
                active.discard(sid)

        for sid, exc_map in feed.calendar_dates.items():
            exc = exc_map.get(target_date)
            if exc == 1:  # service added
                active.add(sid)

        return active


# ---------------------------------------------------------------------------
# GTFS parsing helpers
# ---------------------------------------------------------------------------

def _read_csv_text(zf: zipfile.ZipFile, filename: str) -> str:
    """Read a CSV file from the zip as text, detecting encoding."""
    raw = zf.read(filename)
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            return raw.decode("latin-1")
        except UnicodeDecodeError:
            return raw.decode("utf-8", errors="replace")


def _parse_csv(zf: zipfile.ZipFile, filename: str, parser: Any) -> dict:
    if filename not in zf.namelist():
        return {}
    text = _read_csv_text(zf, filename)
    result: dict = {}
    for row in csv.DictReader(io.StringIO(text)):
        try:
            key, value = parser(row)
            result[key] = value
        except Exception:
            continue
    return result


def _parse_agency(row: dict[str, str]) -> tuple[str, GtfsAgency]:
    agency_id = row.get("agency_id", "1")
    return agency_id, GtfsAgency(agency_id=agency_id, name=row.get("agency_name", agency_id))


def _parse_stop(row: dict[str, str]) -> tuple[str, GtfsStop]:
    return row["stop_id"], GtfsStop(
        stop_id=row["stop_id"],
        name=row.get("stop_name", row["stop_id"]),
        lat=float(row.get("stop_lat", 0)),
        lon=float(row.get("stop_lon", 0)),
    )


def _parse_route(row: dict[str, str]) -> tuple[str, GtfsRoute]:
    return row["route_id"], GtfsRoute(
        route_id=row["route_id"],
        agency_id=row.get("agency_id", "1"),
        short_name=row.get("route_short_name", ""),
        long_name=row.get("route_long_name", ""),
        route_type=int(row.get("route_type", 3)),
    )


def _parse_trip(row: dict[str, str]) -> tuple[str, GtfsTrip]:
    return row["trip_id"], GtfsTrip(
        trip_id=row["trip_id"],
        route_id=row["route_id"],
        service_id=row["service_id"],
        headsign=row.get("trip_headsign", ""),
    )


def _parse_stop_times(zf: zipfile.ZipFile) -> list[GtfsStopTime]:
    if "stop_times.txt" not in zf.namelist():
        return []
    text = _read_csv_text(zf, "stop_times.txt")
    result: list[GtfsStopTime] = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            result.append(GtfsStopTime(
                trip_id=row["trip_id"],
                stop_id=row["stop_id"],
                arrival_seconds=_hhmmss_to_seconds(row.get("arrival_time", "00:00:00")),
                departure_seconds=_hhmmss_to_seconds(row.get("departure_time", "00:00:00")),
                stop_sequence=int(row.get("stop_sequence", 0)),
            ))
        except (KeyError, ValueError):
            continue
    return result


def _parse_calendar(zf: zipfile.ZipFile) -> dict[str, set[date]]:
    text = _read_csv_text(zf, "calendar.txt")
    result: dict[str, set[date]] = {}
    day_fields = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for row in csv.DictReader(io.StringIO(text)):
        try:
            sid = row["service_id"]
            start = date.fromisoformat(row["start_date"])
            end = date.fromisoformat(row["end_date"])
            active_days = {i for i, f in enumerate(day_fields) if row.get(f, "0") == "1"}
            dates: set[date] = set()
            current = start
            while current <= end:
                if current.weekday() in active_days:
                    dates.add(current)
                current += timedelta(days=1)
            result[sid] = dates
        except (KeyError, ValueError):
            continue
    return result


def _parse_calendar_dates(zf: zipfile.ZipFile) -> dict[str, dict[date, int]]:
    text = _read_csv_text(zf, "calendar_dates.txt")
    result: dict[str, dict[date, int]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        try:
            sid = row["service_id"]
            d = date.fromisoformat(row["date"])
            exc = int(row["exception_type"])
            result.setdefault(sid, {})[d] = exc
        except (KeyError, ValueError):
            continue
    return result


def _hhmmss_to_seconds(value: str) -> int:
    parts = value.strip().split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 3600 + int(parts[1]) * 60
    return 0


def _route_type_name(route_type: int) -> str:
    return _ROUTE_TYPE_NAMES.get(route_type, "transit")


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two lat/lng points."""
    import math
    R = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
