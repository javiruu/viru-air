"""GTFS feed probe — manual diagnostic tool for real feed validation.

Usage:
    uv run python -m backend.app.door_to_door.tools.gtfs_probe \\
        --feed ctan_andalucia \\
        --origin "Almería" --destination "Málaga AGP" \\
        --date 2026-07-15

    uv run python -m backend.app.door_to_door.tools.gtfs_probe \\
        --feed mom_treviso \\
        --origin-lat 45.6508 --origin-lng 12.1978 \\
        --dest-lat 45.6669 --dest-lng 12.243 \\
        --date 2026-07-15

Outputs a readable summary:
- Feed stats (stops, routes, trips, stop_times, calendar)
- Nearby stops for origin/destination coordinates
- Matching trips for the target date and time
- Warnings and diagnostics
"""

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Ensure stdout can handle Unicode on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend is on the path when invoked as python -m
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

from app.door_to_door.services.gtfs_feed_service import (
    GtfsFeedDescriptor,
    GtfsFeedService,
    load_feed_descriptors,
)

# Airport coordinates for common Viru airports
AIRPORT_COORDS: dict[str, tuple[float, float]] = {
    "AGP": (36.6749, -4.4991),
    "TSF": (45.6508, 12.1978),
    "MAD": (40.4983, -3.5676),
    "BCN": (41.2974, 2.0833),
}

# City name to coordinates for quick lookup
CITY_COORDS: dict[str, tuple[float, float]] = {
    "almeria": (36.8340, -2.4630),
    "almería": (36.8340, -2.4630),
    "malaga": (36.7213, -4.4215),
    "málaga": (36.7213, -4.4215),
    "treviso": (45.6669, 12.2430),
    "treviso centro": (45.6669, 12.2430),
    "venecia": (45.4408, 12.3155),
    "venice": (45.4408, 12.3155),
    "padua": (45.4064, 11.8768),
    "padova": (45.4064, 11.8768),
}


def resolve_coords(origin_str: str | None, dest_str: str | None,
                   origin_lat: float | None, origin_lng: float | None,
                   dest_lat: float | None, dest_lng: float | None
                   ) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
    """Resolve coordinates from strings or explicit lat/lng."""
    origin_coords = None
    dest_coords = None

    if origin_lat is not None and origin_lng is not None:
        origin_coords = (origin_lat, origin_lng)
    elif origin_str:
        origin_str = origin_str.strip().lower()
        if origin_str.upper() in AIRPORT_COORDS:
            origin_coords = AIRPORT_COORDS[origin_str.upper()]
        elif origin_str in CITY_COORDS:
            origin_coords = CITY_COORDS[origin_str]

    if dest_lat is not None and dest_lng is not None:
        dest_coords = (dest_lat, dest_lng)
    elif dest_str:
        dest_str = dest_str.strip().lower()
        if dest_str.upper() in AIRPORT_COORDS:
            dest_coords = AIRPORT_COORDS[dest_str.upper()]
        elif dest_str in CITY_COORDS:
            dest_coords = CITY_COORDS[dest_str]

    return origin_coords, dest_coords


def print_separator(title: str = "") -> None:
    width = 60
    if title:
        print(f"\n{'=' * width}")
        print(f"  {title}")
        print(f"{'=' * width}")
    else:
        print(f"{'=' * width}")


def probe_feed_stats(feed_service: GtfsFeedService, descriptor: GtfsFeedDescriptor) -> dict:
    """Load a feed and print its statistics."""
    print_separator(f"Feed: {descriptor.id} — {descriptor.name}")
    print(f"  Region:   {descriptor.region}")
    print(f"  URL:      {descriptor.url}")
    print(f"  Source:   {descriptor.source_type}")

    feed = feed_service.load_feed(descriptor)
    if feed is None:
        print("  [FAIL] STATUS: FAILED TO LOAD")
        return {"status": "failed", "feed": None}

    print("  [OK] STATUS: LOADED")
    print(f"  Downloaded: {datetime.fromtimestamp(feed.downloaded_at, tz=timezone.utc).isoformat()}")
    print(f"  Agencies:   {len(feed.agencies)}")
    for aid, agency in list(feed.agencies.items())[:5]:
        print(f"    - [{aid}] {agency.name}")
    print(f"  Stops:      {len(feed.stops)}")
    print(f"  Routes:     {len(feed.routes)}")
    # Count route types
    route_types: dict[str, int] = {}
    for r in feed.routes.values():
        from app.door_to_door.services.gtfs_feed_service import _route_type_name
        rt = _route_type_name(r.route_type)
        route_types[rt] = route_types.get(rt, 0) + 1
    print(f"  Route types: {', '.join(f'{k}={v}' for k, v in sorted(route_types.items()))}")
    print(f"  Trips:      {len(feed.trips)}")
    total_st = sum(len(v) for v in feed.stop_times.values())
    print(f"  Stop times: {total_st} (across {len(feed.stop_times)} trips)")
    print(f"  Calendar services:  {len(feed.calendar)}")
    print(f"  Calendar_dates svc: {len(feed.calendar_dates)}")

    # Sample agencies
    if feed.agencies:
        print("\n  Sample agencies:")
        for aid, agency in list(feed.agencies.items())[:5]:
            print(f"    [{aid}] {agency.name}")

    # Sample stops
    if feed.stops:
        print("\n  Sample stops:")
        for sid, stop in list(feed.stops.items())[:5]:
            print(f"    [{sid}] {stop.name}  ({stop.lat:.4f}, {stop.lon:.4f})")

    return {"status": "loaded", "feed": feed}


def probe_nearby_stops(feed_service: GtfsFeedService, feed_id: str,
                       origin_coords: tuple[float, float] | None,
                       dest_coords: tuple[float, float] | None) -> None:
    """Find nearby stops for origin and destination."""
    if origin_coords:
        lat, lng = origin_coords
        print_separator(f"Nearby stops for ORIGIN ({lat:.4f}, {lng:.4f})")
        stops = feed_service.find_nearby_stops(feed_id, lat, lng)
        if stops:
            for s in stops:
                from app.door_to_door.services.gtfs_feed_service import _haversine_meters
                dist = _haversine_meters(lat, lng, s.lat, s.lon)
                print(f"  [{s.stop_id}] {s.name}  ({s.lat:.4f}, {s.lon:.4f}) — {dist:.0f}m")
        else:
            print(f"  [NONE] No stops found within {feed_service.max_walk_radius}m")

    if dest_coords:
        lat, lng = dest_coords
        print_separator(f"Nearby stops for DESTINATION ({lat:.4f}, {lng:.4f})")
        stops = feed_service.find_nearby_stops(feed_id, lat, lng)
        if stops:
            for s in stops:
                from app.door_to_door.services.gtfs_feed_service import _haversine_meters
                dist = _haversine_meters(lat, lng, s.lat, s.lon)
                print(f"  [{s.stop_id}] {s.name}  ({s.lat:.4f}, {s.lon:.4f}) — {dist:.0f}m")
        else:
            print(f"  [NONE] No stops found within {feed_service.max_walk_radius}m")


def probe_trips(feed_service: GtfsFeedService, feed_id: str,
                origin_coords: tuple[float, float] | None,
                dest_coords: tuple[float, float] | None,
                target_date: date,
                departure_hour: int = 14) -> None:
    """Search for trips between origin-area stops and destination-area stops."""
    if not origin_coords or not dest_coords:
        return

    print_separator(f"Trip search for {target_date} (departing after {departure_hour}:00)")

    from_stops = feed_service.find_nearby_stops(feed_id, *origin_coords)
    to_stops = feed_service.find_nearby_stops(feed_id, *dest_coords)

    if not from_stops or not to_stops:
        print("  [NONE] Cannot search: missing nearby stops on one or both ends")
        return

    # Search the next 2 days in case the target date has no service
    all_trips: list = []
    for day_offset in range(3):
        search_date = target_date + timedelta(days=day_offset)
        earliest = datetime(search_date.year, search_date.month, search_date.day,
                            departure_hour, 0, tzinfo=timezone.utc)
        for from_s in from_stops:
            for to_s in to_stops:
                if from_s.stop_id == to_s.stop_id:
                    continue
                trips = feed_service.find_trips_between(
                    feed_id, from_s.stop_id, to_s.stop_id,
                    target_date=search_date,
                    earliest_departure=earliest,
                )
                for t in trips:
                    all_trips.append((search_date, from_s, to_s, t))
                    if len(all_trips) >= 10:
                        break
                if len(all_trips) >= 10:
                    break
            if len(all_trips) >= 10:
                break
        if all_trips:
            break

    if not all_trips:
        print("  [NONE] No matching trips found for any of the 3 dates searched")
        return        print(f"  [OK] Found {len(all_trips)} trip(s):\n")
    for search_date, from_s, to_s, t in all_trips[:10]:
        print(f"  Date: {search_date}")
        print(f"    From: [{from_s.stop_id}] {from_s.name}")
        print(f"    To:   [{to_s.stop_id}] {to_s.name}")
        print(f"    Route: {t.route_name} ({t.agency_name}) — {t.mode}")
        print(f"    Depart: {t.departure_at.isoformat()}")
        print(f"    Arrive: {t.arrival_at.isoformat()}")
        print(f"    Duration: {t.duration_minutes} min")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GTFS feed diagnostic probe for manual real-feed validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.door_to_door.tools.gtfs_probe --list
  python -m app.door_to_door.tools.gtfs_probe --feed ctan_andalucia --origin "Almería" --dest "Málaga AGP" --date 2026-07-15
  python -m app.door_to_door.tools.gtfs_probe --feed mom_treviso --origin-lat 45.6508 --origin-lng 12.1978 --dest-lat 45.6669 --dest-lng 12.243
        """,
    )
    parser.add_argument("--list", action="store_true", help="List all configured feeds")
    parser.add_argument("--feed", type=str, help="Feed ID to probe")
    parser.add_argument("--origin", type=str, help="Origin city name or IATA airport code")
    parser.add_argument("--dest", "--destination", type=str, help="Destination city name or IATA airport code")
    parser.add_argument("--origin-lat", type=float, help="Origin latitude")
    parser.add_argument("--origin-lng", type=float, help="Origin longitude")
    parser.add_argument("--dest-lat", type=float, help="Destination latitude")
    parser.add_argument("--dest-lng", type=float, help="Destination longitude")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD), default: today")
    parser.add_argument("--hour", type=int, default=14, help="Earliest departure hour, default: 14")
    parser.add_argument("--cache-ttl", type=int, default=0, help="Cache TTL in seconds (0 = always re-download)")
    parser.add_argument("--max-walk", type=int, default=2000, help="Max walk radius in meters")
    parser.add_argument("--max-results", type=int, default=5, help="Max trip results per search")
    parser.add_argument("--json", action="store_true", help="Output as JSON (for scripting)")

    args = parser.parse_args()
    target_date = date.fromisoformat(args.date) if args.date else date.today()

    # List mode
    if args.list:
        descriptors = load_feed_descriptors()
        if not descriptors:
            print("No GTFS feeds configured.")
            return
        print(f"Configured feeds ({len(descriptors)}):\n")
        for d in descriptors:
            print(f"  [{d.id}]")
            print(f"    Name:    {d.name}")
            print(f"    Region:  {d.region}")
            print(f"    URL:     {d.url}")
            print(f"    License: {d.license_url or '—'}")
            print(f"    Attrib:  {d.attribution or '—'}")
            print()
        return

    # Feed probe mode
    descriptors = load_feed_descriptors()
    if not descriptors:
        print("[FAIL] No GTFS feeds configured.")
        print("   Set DOOR_TO_DOOR_GTFS_FEEDS_JSON or DOOR_TO_DOOR_GTFS_FEEDS_FILE")
        print("   or ensure backend/app/door_to_door/providers/gtfs_feeds.json exists.")
        sys.exit(1)

    target_descriptor = None
    if args.feed:
        for d in descriptors:
            if d.id == args.feed:
                target_descriptor = d
                break
        if target_descriptor is None:
            print(f"[FAIL] Feed '{args.feed}' not found in configured feeds.")
            print(f"   Available: {', '.join(d.id for d in descriptors)}")
            sys.exit(1)
    else:
        target_descriptor = descriptors[0]
        print(f"[INFO] No --feed specified, using first configured feed: {target_descriptor.id}")

    feed_service = GtfsFeedService(
        cache_ttl_seconds=args.cache_ttl,
        max_walk_radius_meters=args.max_walk,
        max_results=args.max_results,
    )

    # 1. Feed stats
    result = probe_feed_stats(feed_service, target_descriptor)
    feed = result.get("feed")

    if feed is None:
        print("\n[FAIL] Feed failed to load. Diagnostic complete.")
        sys.exit(1)

    # 2. Resolve coordinates
    origin_coords, dest_coords = resolve_coords(
        args.origin, args.dest,
        args.origin_lat, args.origin_lng,
        args.dest_lat, args.dest_lng,
    )
    if origin_coords:
        print(f"\n  Origin coords:    {origin_coords[0]:.4f}, {origin_coords[1]:.4f}")
    if dest_coords:
        print(f"  Destination coords: {dest_coords[0]:.4f}, {dest_coords[1]:.4f}")

    # 3. Nearby stops
    probe_nearby_stops(feed_service, target_descriptor.id, origin_coords, dest_coords)

    # 4. Trip search
    probe_trips(feed_service, target_descriptor.id, origin_coords, dest_coords,
                target_date, args.hour)

    print_separator("Diagnostic complete")


if __name__ == "__main__":
    main()
