from datetime import date, datetime, timezone

from app.door_to_door.services.gtfs_feed_service import GtfsFeedService, GtfsStop, GtfsTransitLeg
from app.door_to_door.tools.gtfs_probe import probe_trips, resolve_coords


class FakeGtfsFeedService(GtfsFeedService):
    def __init__(self) -> None:
        self.max_results = 1

    def find_nearby_stops(self, feed_id: str, latitude: float, longitude: float) -> list[GtfsStop]:
        del feed_id, longitude
        stop = "origin" if latitude == 40.0 else "destination"
        return [GtfsStop(stop_id=stop, name=stop.title(), lat=latitude, lon=0.0)]

    def find_trips_between(
        self,
        feed_id: str,
        from_stop_id: str,
        to_stop_id: str,
        target_date: date,
        earliest_departure: datetime | None = None,
        latest_arrival: datetime | None = None,
    ) -> list[GtfsTransitLeg]:
        del feed_id, from_stop_id, to_stop_id, target_date, earliest_departure, latest_arrival
        return [
            GtfsTransitLeg(
                feed_id="test-feed",
                route_name="Airport express",
                agency_name="Transit",
                mode="train",
                departure_at=datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc),
                arrival_at=datetime(2026, 7, 15, 14, 30, tzinfo=timezone.utc),
                duration_minutes=30,
                from_stop_name="Origin",
                to_stop_name="Destination",
                from_stop_id="origin",
                to_stop_id="destination",
            ),
            GtfsTransitLeg(
                feed_id="test-feed",
                route_name="Airport local",
                agency_name="Transit",
                mode="bus",
                departure_at=datetime(2026, 7, 15, 14, 5, tzinfo=timezone.utc),
                arrival_at=datetime(2026, 7, 15, 15, 0, tzinfo=timezone.utc),
                duration_minutes=55,
                from_stop_name="Origin",
                to_stop_name="Destination",
                from_stop_id="origin",
                to_stop_id="destination",
            ),
        ]


def test_probe_trips_prints_found_trip_and_respects_configured_limit(capsys) -> None:
    probe_trips(
        FakeGtfsFeedService(),
        "test-feed",
        (40.0, -3.0),
        (41.0, -4.0),
        date(2026, 7, 15),
    )

    output = capsys.readouterr().out
    assert "[OK] Found 1 trip(s):" in output
    assert "Route: Airport express (Transit) — train" in output
    assert "Airport local" not in output


def test_probe_example_city_names_resolve_to_origin_and_destination_coordinates() -> None:
    origin, destination = resolve_coords("Almería", "Málaga", None, None, None, None)

    assert origin == (36.8340, -2.4630)
    assert destination == (36.7213, -4.4215)
