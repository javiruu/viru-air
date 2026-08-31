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
# Hard cap: walk radius must not exceed this value regardless of env
MAX_WALK_RADIUS_HARD_CAP = 5000  # 5 km
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
    api_key_env: str | None = None
    auth_header_name: str | None = None
    auth_value_prefix: str = ""
    # If "json_presigned", the response body is a JSON string containing a
    # presigned URL to follow (e.g. NAP España /api/Fichero/downloadLink).
    # When unset/None, the response body is the file itself.
    response_format: str | None = None


def load_feed_descriptors() -> list[GtfsFeedDescriptor]:
    """Load feed descriptors from DOOR_TO_DOOR_GTFS_FEEDS_JSON env or DOOR_TO_DOOR_GTFS_FEEDS_FILE.

    Priority:
    1. DOOR_TO_DOOR_GTFS_FEEDS_JSON env var (inline JSON string)
    2. DOOR_TO_DOOR_GTFS_FEEDS_FILE env var (path to JSON file)
    3. Default manifest file at providers/gtfs_feeds.json (if exists)
    """
    raw = os.getenv("DOOR_TO_DOOR_GTFS_FEEDS_JSON", "")
    if raw.strip():
        return _parse_descriptors_json(raw)

    file_path = os.getenv("DOOR_TO_DOOR_GTFS_FEEDS_FILE", "")
    if file_path.strip():
        try:
            raw = Path(file_path).read_text(encoding="utf-8")
            return _parse_descriptors_json(raw)
        except (OSError, json.JSONDecodeError):
            logger.warning("gtfs_feed_descriptors_file_invalid", extra={"path": file_path})
            return []

    # Fallback: look for default manifest next to this module
    default_manifest = Path(__file__).resolve().parent.parent / "providers" / "gtfs_feeds.json"
    if default_manifest.exists():
        try:
            raw = default_manifest.read_text(encoding="utf-8")
            return _parse_descriptors_json(raw)
        except (OSError, json.JSONDecodeError):
            pass

    return []


def _parse_descriptors_json(raw: str) -> list[GtfsFeedDescriptor]:
    """Parse JSON string into feed descriptors, skipping invalid entries."""
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("gtfs_feed_descriptors_invalid_json")
        return []
    descriptors: list[GtfsFeedDescriptor] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        feed_id = item.get("id")
        url = item.get("url")
        if not isinstance(feed_id, str) or not feed_id.strip() or not isinstance(url, str) or not url.strip():
            continue
        name = item.get("name", feed_id)
        region = item.get("region", "")
        source_type = item.get("source_type", "open_data")
        auth_value_prefix = item.get("auth_value_prefix", "")
        descriptors.append(
            GtfsFeedDescriptor(
                id=feed_id,
                name=name if isinstance(name, str) and name.strip() else feed_id,
                region=region if isinstance(region, str) else "",
                url=url,
                source_type=source_type if isinstance(source_type, str) else "open_data",
                license_url=item.get("license_url") if isinstance(item.get("license_url"), str) else None,
                attribution=item.get("attribution") if isinstance(item.get("attribution"), str) else None,
                api_key_env=item.get("api_key_env") if isinstance(item.get("api_key_env"), str) else None,
                auth_header_name=item.get("auth_header_name") if isinstance(item.get("auth_header_name"), str) else None,
                auth_value_prefix=auth_value_prefix if isinstance(auth_value_prefix, str) else "",
                response_format=item.get("response_format") if isinstance(item.get("response_format"), str) else None,
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
class GtfsFareAttribute:
    fare_id: str
    price: float
    currency_type: str
    payment_method: int  # 0=on board, 1=before boarding
    transfers: int  # 0=no transfers, 1=1 transfer, 2=2 transfers, empty=unlimited
    agency_id: str | None = None
    transfer_duration: int | None = None  # seconds


@dataclass
class GtfsFareRule:
    fare_id: str
    route_id: str | None  # None = applies to all routes
    origin_id: str | None  # zone ID
    destination_id: str | None  # zone ID
    contains_id: str | None  # zone ID that must be contained in the journey


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
    fare_attributes: dict[str, GtfsFareAttribute] = field(default_factory=dict)  # fare_id -> fare
    fare_rules: list[GtfsFareRule] = field(default_factory=list)


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
    route_id: str = ""  # For fare lookup
    lowest_price: float | None = None  # Confirmed fare from feed, if available
    currency: str = "EUR"


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
        raw_walk = max_walk_radius_meters if max_walk_radius_meters is not None else DEFAULT_MAX_WALK_RADIUS
        self.max_walk_radius = min(raw_walk, MAX_WALK_RADIUS_HARD_CAP)
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
                parsed_feed = self._parse_feed(cached_path, descriptor.id)
                if parsed_feed is not None:
                    self._feeds[descriptor.id] = parsed_feed
                    return parsed_feed

        try:
            raw_bytes = self._download(descriptor)
        except Exception:
            logger.warning("gtfs_download_failed", extra={"feed_id": descriptor.id, "url": descriptor.url})
            # Try stale cache
            if cached_path.exists():
                parsed_feed = self._parse_feed(cached_path, descriptor.id)
                if parsed_feed is not None:
                    parsed_feed.downloaded_at = time.time()  # mark as stale but usable
                    self._feeds[descriptor.id] = parsed_feed
                    return parsed_feed
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
        parsed_feed = self._parse_feed(cached_path, descriptor.id)
        if parsed_feed is not None:
            self._feeds[descriptor.id] = parsed_feed
        return parsed_feed

    def find_nearby_stops(self, feed_id: str, lat: float, lng: float) -> list[GtfsStop]:
        """Find stops within max_walk_radius of the given coordinates, sorted nearest first.

        Returns all stops within radius (up to a generous cap) so that downstream
        trip matching has enough candidates to find connecting routes.
        """
        feed = self._feeds.get(feed_id)
        if feed is None:
            return []
        stops: list[tuple[float, GtfsStop]] = []
        for stop in feed.stops.values():
            dist = _haversine_meters(lat, lng, stop.lat, stop.lon)
            if dist <= self.max_walk_radius:
                stops.append((dist, stop))
        stops.sort(key=lambda item: item[0])
        # Cap at a generous maximum to avoid explosion, but much higher than max_results
        return [s for _, s in stops[:50]]

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
        return self.find_trips_between_any(
            feed_id=feed_id,
            from_stop_ids={from_stop_id},
            to_stop_ids={to_stop_id},
            target_date=target_date,
            earliest_departure=earliest_departure,
            latest_arrival=latest_arrival,
        )

    def find_trips_between_any(
        self,
        feed_id: str,
        from_stop_ids: set[str],
        to_stop_ids: set[str],
        target_date: date,
        earliest_departure: datetime | None = None,
        latest_arrival: datetime | None = None,
    ) -> list[GtfsTransitLeg]:
        """Find direct trips that serve any from_stop_id before any to_stop_id on target_date.

        More efficient than calling find_trips_between for every pair: builds index once.
        """
        feed = self._feeds.get(feed_id)
        if feed is None:
            return []

        active_services = self._active_services(feed, target_date)
        if not active_services:
            return []

        earliest_seconds: int | None = None
        latest_seconds: int | None = None

        if earliest_departure is not None:
            earliest_seconds = earliest_departure.hour * 3600 + earliest_departure.minute * 60
        if latest_arrival is not None:
            latest_seconds = latest_arrival.hour * 3600 + latest_arrival.minute * 60

        results: list[GtfsTransitLeg] = []

        for trip_id, st_list in feed.stop_times.items():
            trip = feed.trips.get(trip_id)
            if trip is None or trip.service_id not in active_services:
                continue

            # Find the first from-stop that has a to-stop after it in the sequence.
            # Iterate stops in order; track the earliest unmatched from-stop.
            from_st: GtfsStopTime | None = None
            to_st: GtfsStopTime | None = None
            for st in st_list:
                if st.stop_id in from_stop_ids and from_st is None:
                    from_st = st
                if from_st is not None and st.stop_id in to_stop_ids and st.stop_id != from_st.stop_id:
                    to_st = st
                    if to_st.arrival_seconds > from_st.departure_seconds:
                        break  # first valid pair found
                    # Arrival not after departure — keep searching for a later dest stop
                    to_st = None
            if from_st is None or to_st is None:
                continue

            dep_sec = from_st.departure_seconds
            arr_sec = to_st.arrival_seconds

            # GTFS allows times ≥ 24:00:00 for trips past midnight.
            # Normalize to 0–23 hour range by wrapping to the next day.
            dep_day_offset = dep_sec // 86400
            arr_day_offset = arr_sec // 86400
            dep_sec_norm = dep_sec % 86400
            arr_sec_norm = arr_sec % 86400

            # Time window filter — use normalized values so overnight trips
            # are compared correctly within the target date's 0-86399 range.
            if earliest_seconds is not None and dep_sec_norm < earliest_seconds:
                continue
            if latest_seconds is not None and arr_sec_norm > latest_seconds:
                continue

            route = feed.routes.get(trip.route_id)
            if route is None:
                continue
            agency = feed.agencies.get(route.agency_id)
            mode = _route_type_name(route.route_type)
            duration = arr_sec - dep_sec

            dep_dt = datetime(
                target_date.year, target_date.month, target_date.day,
                dep_sec_norm // 3600, (dep_sec_norm % 3600) // 60, dep_sec_norm % 60,
                tzinfo=timezone.utc,
            ) + timedelta(days=dep_day_offset)
            arr_dt = datetime(
                target_date.year, target_date.month, target_date.day,
                arr_sec_norm // 3600, (arr_sec_norm % 3600) // 60, arr_sec_norm % 60,
                tzinfo=timezone.utc,
            ) + timedelta(days=arr_day_offset)

            from_stop_obj = feed.stops.get(from_st.stop_id)
            to_stop_obj = feed.stops.get(to_st.stop_id)

            results.append(
                GtfsTransitLeg(
                    feed_id=feed_id,
                    agency_name=agency.name if agency else route.agency_id,
                    route_name=route.short_name or route.long_name or route.route_id,
                    mode=mode,
                    departure_at=dep_dt,
                    arrival_at=arr_dt,
                    duration_minutes=int(duration / 60),
                    from_stop_name=from_stop_obj.name if from_stop_obj else from_st.stop_id,
                    to_stop_name=to_stop_obj.name if to_stop_obj else to_st.stop_id,
                    from_stop_id=from_st.stop_id,
                    to_stop_id=to_st.stop_id,
                    route_id=trip.route_id,
                )
            )

        # Sort by departure time
        results.sort(key=lambda leg: leg.departure_at)

        # Enrich legs with fare data
        for leg in results:
            fare = self.lookup_fare(feed_id, leg.from_stop_id, leg.to_stop_id, leg.route_id)
            if fare is not None:
                leg.lowest_price = fare.price
                leg.currency = fare.currency_type

        return results[: self.max_results]

    # ---- fare lookup (Fase 5) ----

    def lookup_fare(
        self,
        feed_id: str,
        from_stop_id: str,
        to_stop_id: str,
        route_id: str,
    ) -> GtfsFareAttribute | None:
        """Find the lowest confirmed fare for a trip between two stops on a route.

        GTFS fare rules match by route_id and/or zone IDs. We try:
        1. Exact match: route + origin zone + destination zone
        2. Route-only match (no zone restrictions)
        3. Zone-only match (no route restriction, for flat-fare systems)
        4. Fallback to the first fare attribute if no rules match
        """
        feed = self._feeds.get(feed_id)
        if feed is None:
            return None
        if not feed.fare_attributes:
            return None

        # Build a zone map from stops.txt zone_id field (if available)
        # Most feeds don't include zone_id in stops; fare rules often use zone_id = "" for all
        candidates: list[GtfsFareAttribute] = []

        for rule in feed.fare_rules:
            # Check route match
            route_match = rule.route_id is None or rule.route_id == "" or rule.route_id == route_id
            if not route_match:
                continue

            # Check zone match (origin_id/destination_id are often empty = any zone)
            zone_ok = True
            if rule.origin_id and rule.origin_id != "":
                zone_ok = False  # We don't have per-stop zone data; skip zone-specific rules
            if rule.destination_id and rule.destination_id != "":
                zone_ok = False
            if not zone_ok:
                continue

            fare = feed.fare_attributes.get(rule.fare_id)
            if fare is not None:
                candidates.append(fare)

        if candidates:
            # Return the cheapest fare
            candidates.sort(key=lambda f: f.price)
            return candidates[0]

        # Last resort: return the first fare attribute (many feeds have a single flat fare)
        first = next(iter(feed.fare_attributes.values()), None)
        return first

    # ---- internal ----

    def _cache_path(self, descriptor: GtfsFeedDescriptor) -> Path:
        name_hash = hashlib.sha256(descriptor.id.encode()).hexdigest()[:16]
        return self.cache_dir / f"{descriptor.id}_{name_hash}.zip"

    @staticmethod
    def _download(descriptor: GtfsFeedDescriptor) -> bytes:
        headers: dict[str, str] = {}
        if descriptor.api_key_env and descriptor.auth_header_name:
            api_key = os.getenv(descriptor.api_key_env, "")
            if api_key:
                value = f"{descriptor.auth_value_prefix}{api_key}"
                headers[descriptor.auth_header_name] = value
            else:
                logger.debug(
                    "gtfs_auth_key_missing",
                    extra={"feed_id": descriptor.id, "env_var": descriptor.api_key_env},
                )
        resp = httpx.get(
            descriptor.url,
            headers=headers,
            timeout=DEFAULT_DOWNLOAD_TIMEOUT,
            follow_redirects=True,
        )
        resp.raise_for_status()
        # Some endpoints (e.g. NAP España /api/Fichero/downloadLink/{id}) respond
        # with the presigned URL as either:
        #   - application/json wrapping a JSON string: "https://..."  (when Accept: application/json)
        #   - text/plain with the URL directly:        https://...     (default Accept)
        # The response_format=json_presigned flag enables the redirect; the body
        # is then interpreted as the URL to follow to obtain the actual file.
        if descriptor.response_format == "json_presigned":
            body_text = resp.content.decode("utf-8", errors="replace").strip()
            try:
                presigned_url = json.loads(body_text)
            except (json.JSONDecodeError, ValueError):
                # Body is the URL directly (plain text)
                presigned_url = body_text
            if not isinstance(presigned_url, str) or not presigned_url:
                logger.warning(
                    "gtfs_presigned_url_invalid",
                    extra={"feed_id": descriptor.id, "type": type(presigned_url).__name__},
                )
                return resp.content
            resp2 = httpx.get(
                presigned_url,
                timeout=DEFAULT_DOWNLOAD_TIMEOUT,
                follow_redirects=True,
            )
            resp2.raise_for_status()
            return resp2.content
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
                # Fase 5: parse fare data when available
                fare_attributes: dict[str, GtfsFareAttribute] = {}
                fare_rules: list[GtfsFareRule] = []
                if "fare_attributes.txt" in zf.namelist():
                    fare_attributes = _parse_csv(zf, "fare_attributes.txt", _parse_fare_attribute)
                if "fare_rules.txt" in zf.namelist():
                    fare_rules = _parse_fare_rules(zf)

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
                fare_attributes=fare_attributes,
                fare_rules=fare_rules,
            )
        except Exception:
            logger.exception("gtfs_parse_failed", extra={"feed_id": feed_id})
            return None

    @staticmethod
    def _active_services(feed: ParsedGtfsFeed, target_date: date) -> set[str]:
        """Determine which service_ids are active on target_date.

        Priority:
        1. calendar.txt: add service_ids whose date range + day-of-week covers target_date
        2. calendar_dates.txt exception_type=2: remove service_id for target_date
        3. calendar_dates.txt exception_type=1: add service_id for target_date

        If calendar.txt is empty (feed uses calendar_dates exclusively),
        only exception_type=1 entries determine active services.
        """
        active: set[str] = set()

        # calendar.txt — regular schedule
        for sid, dates in feed.calendar.items():
            if target_date in dates:
                active.add(sid)

        # calendar_dates.txt — exceptions (removals first, then additions)
        for sid, exc_map in feed.calendar_dates.items():
            exc = exc_map.get(target_date)
            if exc == 2:  # service removed for this date
                active.discard(sid)

        for sid, exc_map in feed.calendar_dates.items():
            exc = exc_map.get(target_date)
            if exc == 1:  # service added for this date
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


def _parse_fare_attribute(row: dict[str, str]) -> tuple[str, GtfsFareAttribute]:
    return row["fare_id"], GtfsFareAttribute(
        fare_id=row["fare_id"],
        price=float(row.get("price", 0)),
        currency_type=row.get("currency_type", "EUR"),
        payment_method=int(row.get("payment_method", 0)),
        transfers=int(row.get("transfers", 0)) if row.get("transfers", "").strip() else 99,
        agency_id=row.get("agency_id"),
        transfer_duration=int(row["transfer_duration"]) if row.get("transfer_duration", "").strip() else None,
    )


def _parse_fare_rules(zf: zipfile.ZipFile) -> list[GtfsFareRule]:
    if "fare_rules.txt" not in zf.namelist():
        return []
    text = _read_csv_text(zf, "fare_rules.txt")
    result: list[GtfsFareRule] = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            result.append(GtfsFareRule(
                fare_id=row["fare_id"],
                route_id=row.get("route_id") or None,
                origin_id=row.get("origin_id") or None,
                destination_id=row.get("destination_id") or None,
                contains_id=row.get("contains_id") or None,
            ))
        except KeyError:
            continue
    return result


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
