from datetime import date, datetime, time, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.time import utc_now_naive
from app.infrastructure.db.models import FlightOperationalSnapshot, WatchTrackedFlightLeg
from app.infrastructure.db.session import get_db
from app.main import app
from tests.helpers import register_and_token


def test_watchlist_live_response_predicts_delay_from_shared_incoming_aircraft(
    client: TestClient,
) -> None:
    # Given: two exact flights share a registration and the inbound aircraft is running late.
    travel_date = date.today() + timedelta(days=1)
    target_departure = datetime.combine(travel_date, time(hour=12))
    inbound_scheduled_arrival = datetime.combine(travel_date, time(hour=10, minute=30))
    inbound_estimated_arrival = datetime.combine(travel_date, time(hour=11, minute=40))
    token = register_and_token(client, email="rotation-prediction@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    inbound_watch = client.post(
        "/api/v1/search/save-result",
        headers=headers,
        json={
            "origin_iata": "BCN",
            "destination_iata": "MAD",
            "travel_date": travel_date.isoformat(),
            "price_total": 64,
            "currency": "EUR",
            "legs": [
                {
                    "flight_number": "IB1234",
                    "origin_iata": "BCN",
                    "destination_iata": "MAD",
                    "departure_at": f"{travel_date.isoformat()}T09:10:00Z",
                    "arrival_at": f"{travel_date.isoformat()}T10:30:00Z",
                }
            ],
        },
    )
    target_watch = client.post(
        "/api/v1/search/save-result",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "FCO",
            "travel_date": travel_date.isoformat(),
            "price_total": 92,
            "currency": "EUR",
            "legs": [
                {
                    "flight_number": "IB3230",
                    "origin_iata": "MAD",
                    "destination_iata": "FCO",
                    "departure_at": f"{travel_date.isoformat()}T12:00:00Z",
                    "arrival_at": f"{travel_date.isoformat()}T14:25:00Z",
                }
            ],
        },
    )
    assert inbound_watch.status_code == 200
    assert target_watch.status_code == 200

    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        inbound_leg = db.scalar(
            select(WatchTrackedFlightLeg).where(
                WatchTrackedFlightLeg.watch_id == inbound_watch.json()["watch_id"]
            )
        )
        target_leg = db.scalar(
            select(WatchTrackedFlightLeg).where(
                WatchTrackedFlightLeg.watch_id == target_watch.json()["watch_id"]
            )
        )
        assert inbound_leg is not None
        assert target_leg is not None
        observed_at = utc_now_naive()
        db.add_all(
            [
                FlightOperationalSnapshot(
                    flight_instance_fingerprint=inbound_leg.flight_instance_fingerprint,
                    provider="aviationstack",
                    provider_flight_id="inbound-ib1234",
                    flight_number="IB1234",
                    status="active",
                    status_raw="active",
                    observed_at=observed_at,
                    expires_at=observed_at + timedelta(minutes=2),
                    scheduled_departure_at=datetime.combine(travel_date, time(hour=9, minute=10)),
                    actual_departure_at=datetime.combine(travel_date, time(hour=10, minute=20)),
                    scheduled_arrival_at=inbound_scheduled_arrival,
                    estimated_arrival_at=inbound_estimated_arrival,
                    arrival_delay_minutes=70,
                    registration="EC-ROT",
                    aircraft_iata="A320",
                    aircraft_icao="A320",
                    data_quality="status_only",
                ),
                FlightOperationalSnapshot(
                    flight_instance_fingerprint=target_leg.flight_instance_fingerprint,
                    provider="aviationstack",
                    provider_flight_id="target-ib3230",
                    flight_number="IB3230",
                    status="scheduled",
                    status_raw="scheduled",
                    observed_at=observed_at,
                    expires_at=observed_at + timedelta(minutes=5),
                    scheduled_departure_at=target_departure,
                    scheduled_arrival_at=datetime.combine(travel_date, time(hour=14, minute=25)),
                    registration="EC-ROT",
                    aircraft_iata="A320",
                    aircraft_icao="A320",
                    data_quality="status_only",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()
        next(generator, None)

    # When: the selected Watch asks only for persisted live state.
    response = client.get(
        f"/api/v1/watchlist/{target_watch.json()['watch_id']}/live?refresh=false",
        headers=headers,
    )

    # Then: the response explains the high delay risk from the exact incoming rotation.
    assert response.status_code == 200
    prediction = response.json()["legs"][0]["delay_prediction"]
    assert prediction["status"] == "available"
    assert prediction["model_version"] == "viru_rotation_v1"
    assert prediction["risk"] == "high"
    assert prediction["risk_score"] == 90
    assert prediction["predicted_delay_min_minutes"] == 20
    assert prediction["predicted_delay_max_minutes"] == 40
    assert prediction["incoming_aircraft"]["registration"] == "EC-ROT"
    assert prediction["incoming_aircraft"]["flight_number"] == "IB1234"
    assert prediction["incoming_aircraft"]["origin_iata"] == "BCN"
    assert prediction["incoming_aircraft"]["destination_iata"] == "MAD"


def test_watchlist_delay_prediction_does_not_reveal_another_users_rotation(
    client: TestClient,
) -> None:
    # Given: one user's incoming flight shares a registration with another user's target.
    travel_date = date.today() + timedelta(days=1)
    inbound_token = register_and_token(client, email="rotation-owner@viru.dev")
    target_token = register_and_token(client, email="rotation-private@viru.dev")
    inbound_watch = client.post(
        "/api/v1/search/save-result",
        headers={"Authorization": f"Bearer {inbound_token}"},
        json={
            "origin_iata": "BCN",
            "destination_iata": "MAD",
            "travel_date": travel_date.isoformat(),
            "price_total": 64,
            "currency": "EUR",
            "legs": [
                {
                    "flight_number": "IB1234",
                    "origin_iata": "BCN",
                    "destination_iata": "MAD",
                    "departure_at": f"{travel_date.isoformat()}T09:10:00Z",
                    "arrival_at": f"{travel_date.isoformat()}T10:30:00Z",
                }
            ],
        },
    )
    target_watch = client.post(
        "/api/v1/search/save-result",
        headers={"Authorization": f"Bearer {target_token}"},
        json={
            "origin_iata": "MAD",
            "destination_iata": "FCO",
            "travel_date": travel_date.isoformat(),
            "price_total": 92,
            "currency": "EUR",
            "legs": [
                {
                    "flight_number": "IB3230",
                    "origin_iata": "MAD",
                    "destination_iata": "FCO",
                    "departure_at": f"{travel_date.isoformat()}T12:00:00Z",
                    "arrival_at": f"{travel_date.isoformat()}T14:25:00Z",
                }
            ],
        },
    )
    assert inbound_watch.status_code == 200
    assert target_watch.status_code == 200

    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        inbound_leg = db.scalar(
            select(WatchTrackedFlightLeg).where(
                WatchTrackedFlightLeg.watch_id == inbound_watch.json()["watch_id"]
            )
        )
        target_leg = db.scalar(
            select(WatchTrackedFlightLeg).where(
                WatchTrackedFlightLeg.watch_id == target_watch.json()["watch_id"]
            )
        )
        assert inbound_leg is not None
        assert target_leg is not None
        observed_at = utc_now_naive()
        db.add_all(
            [
                FlightOperationalSnapshot(
                    flight_instance_fingerprint=inbound_leg.flight_instance_fingerprint,
                    provider="aviationstack",
                    status="active",
                    observed_at=observed_at,
                    expires_at=observed_at + timedelta(minutes=2),
                    scheduled_departure_at=datetime.combine(travel_date, time(hour=9, minute=10)),
                    scheduled_arrival_at=datetime.combine(travel_date, time(hour=10, minute=30)),
                    estimated_arrival_at=datetime.combine(travel_date, time(hour=11, minute=40)),
                    registration="EC-PRIVATE",
                    data_quality="status_only",
                ),
                FlightOperationalSnapshot(
                    flight_instance_fingerprint=target_leg.flight_instance_fingerprint,
                    provider="aviationstack",
                    status="scheduled",
                    observed_at=observed_at,
                    expires_at=observed_at + timedelta(minutes=5),
                    scheduled_departure_at=datetime.combine(travel_date, time(hour=12)),
                    scheduled_arrival_at=datetime.combine(travel_date, time(hour=14, minute=25)),
                    registration="EC-PRIVATE",
                    data_quality="status_only",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()
        next(generator, None)

    # When: the target owner asks for persisted live state.
    response = client.get(
        f"/api/v1/watchlist/{target_watch.json()['watch_id']}/live?refresh=false",
        headers={"Authorization": f"Bearer {target_token}"},
    )

    # Then: Viru withholds the other user's route instead of predicting from it.
    prediction = response.json()["legs"][0]["delay_prediction"]
    assert prediction == {
        "status": "insufficient_data",
        "model_version": "viru_rotation_v1",
        "reason": "incoming_not_found",
    }
