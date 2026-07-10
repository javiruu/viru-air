import datetime as dt

from app.domain.entities import ProviderFlight
from app.services.quick_search_cache_service import deserialize_flights, serialize_flights


def test_provider_flight_cache_roundtrip_preserves_normalized_contract() -> None:
    flight = ProviderFlight(
        price=75.99,
        currency="EUR",
        departure_time_local="18:45",
        captured_at=dt.datetime(2026, 7, 10, 12, 30),
        source="vueling-public-availability",
        provider="vueling",
        origin_iata="BCN",
        destination_iata="ORY",
        travel_date=dt.date(2026, 7, 14),
        deeplink_url="https://tickets.vueling.com/booking/flightSearch?o=BCN&d=ORY",
        carrier_code="VY",
        flight_number=None,
    )

    payload = serialize_flights([flight])

    assert payload == [
        {
            "price": 75.99,
            "currency": "EUR",
            "departure_time_local": "18:45",
            "captured_at": "2026-07-10T12:30:00",
            "source": "vueling-public-availability",
            "provider": "vueling",
            "origin_iata": "BCN",
            "destination_iata": "ORY",
            "travel_date": "2026-07-14",
            "deeplink": "https://tickets.vueling.com/booking/flightSearch?o=BCN&d=ORY",
            "deeplink_url": "https://tickets.vueling.com/booking/flightSearch?o=BCN&d=ORY",
            "carrier_code": "VY",
            "flight_number": None,
        }
    ]

    restored = deserialize_flights(payload)[0]

    assert restored.provider == "vueling"
    assert restored.origin_iata == "BCN"
    assert restored.destination_iata == "ORY"
    assert restored.travel_date == "2026-07-14"
    assert restored.deeplink_url == "https://tickets.vueling.com/booking/flightSearch?o=BCN&d=ORY"
    assert restored.carrier_code == "VY"
    assert restored.flight_number is None


def test_provider_flight_cache_deserializes_legacy_deeplink_key() -> None:
    restored = deserialize_flights(
        [
            {
                "price": 42.5,
                "currency": "EUR",
                "departure_time_local": "06:30",
                "captured_at": "2026-07-10T12:30:00",
                "source": "ryanair-public-availability",
                "provider": "ryanair",
                "origin_iata": "MAD",
                "destination_iata": "DUB",
                "travel_date": "2026-06-14",
                "deeplink": "https://www.ryanair.com/es-es/trip/flights/select",
                "carrier_code": "FR",
                "flight_number": "FR 7032",
            }
        ]
    )[0]

    assert restored.deeplink_url == "https://www.ryanair.com/es-es/trip/flights/select"
    assert restored.carrier_code == "FR"
    assert restored.flight_number == "FR 7032"
