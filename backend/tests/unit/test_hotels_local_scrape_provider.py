from __future__ import annotations

from datetime import date

from app.hotels.activation import resolve_hotel_activation
from app.hotels.ingestion import resolve_hotel_provider
from app.hotels.local_scrape_provider import LocalHtmlHotelProviderAdapter


def test_local_html_provider_extracts_a_declared_total_stay_offer(tmp_path) -> None:
    # Given
    page = tmp_path / "hotel.html"
    page.write_text(
        """
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Hotel",
          "@id": "https://example.test/hotels/sol",
          "name": "Hotel Sol Local",
          "address": {
            "@type": "PostalAddress",
            "streetAddress": "Calle Sol 1",
            "addressLocality": "Madrid",
            "addressCountry": "ES"
          },
          "geo": {"@type": "GeoCoordinates", "latitude": 40.4168, "longitude": -3.7038},
          "starRating": {"@type": "Rating", "ratingValue": 4},
          "makesOffer": {
            "@type": "Offer",
            "@id": "sol-standard-total",
            "name": "Doble con desayuno",
            "price": "240.00",
            "priceCurrency": "EUR",
            "availability": "https://schema.org/InStock",
            "description": "Cancelación gratuita hasta 48 horas antes",
            "priceSpecification": {"priceType": "total_stay"}
          }
        }
        </script>
        """,
        encoding="utf-8",
    )

    # When
    provider = LocalHtmlHotelProviderAdapter(
        fixture_path=str(page),
        check_in=date(2026, 9, 10),
        check_out=date(2026, 9, 12),
        guests=2,
    )
    hotels = provider.fetch_hotels()

    # Then
    assert provider.is_enabled() is True
    assert len(hotels) == 1
    assert hotels[0].provider_hotel_id == "https://example.test/hotels/sol"
    assert hotels[0].city == "Madrid"
    assert hotels[0].rates[0].amount_total == 240.0
    assert hotels[0].rates[0].price_semantics == "total"
    assert hotels[0].rates[0].conditions_completeness == "complete"


def test_local_html_provider_keeps_ambiguous_price_untrackable(tmp_path) -> None:
    # Given
    page = tmp_path / "hotel.html"
    page.write_text(
        """
        <script type="application/ld+json">
        {
          "@type": "Hotel",
          "@id": "local-hotel-2",
          "name": "Hotel Local",
          "address": {"addressLocality": "Malaga", "addressCountry": "ES"},
          "offers": {"price": "99", "priceCurrency": "EUR"}
        }
        </script>
        """,
        encoding="utf-8",
    )

    # When
    provider = LocalHtmlHotelProviderAdapter(
        fixture_path=str(page),
        check_in=date(2026, 9, 10),
        check_out=date(2026, 9, 12),
    )
    hotels = provider.fetch_hotels()

    # Then
    rate = hotels[0].rates[0]
    assert rate.price_semantics == "unknown"
    assert rate.amount_total is None
    assert rate.conditions_completeness == "partial"


def test_local_html_provider_ignores_invalid_offers_and_normalizes_currency(tmp_path) -> None:
    # Given
    page = tmp_path / "hotel.html"
    page.write_text(
        """
        <script type="application/ld+json">
        {
          "@type": "Hotel",
          "@id": "local-hotel-3",
          "name": "Hotel Seguro",
          "address": {"addressLocality": "Valencia", "addressCountry": "ES"},
          "offers": [
            null,
            "not-an-offer",
            {"price": "NaN", "priceCurrency": "EUR"},
            {"price": "Infinity", "priceCurrency": "EUR"},
            {"price": "1,99", "priceCurrency": "EUR", "priceSpecification": {"priceType": "total"}},
            {"price": "1.234,56", "priceCurrency": "EUR", "priceSpecification": {"priceType": "total"}},
            {"price": "12 34", "priceCurrency": "EUR", "priceSpecification": {"priceType": "total"}},
            {"@id": "valid-total", "name": "Doble", "price": "180", "priceCurrency": "EUR",
             "description": "Total con cancelaciÃ³n", "priceSpecification": {"priceType": "total"}}
          ]
        }
        </script>
        """,
        encoding="utf-8",
    )
    provider = LocalHtmlHotelProviderAdapter(
        fixture_path=str(page),
        check_in=date(2026, 9, 10),
        check_out=date(2026, 9, 12),
    )

    # When
    rates = provider.fetch_hotel_rates(
        "local-hotel-3",
        date(2026, 9, 10),
        date(2026, 9, 12),
        currency=" eur ",
    )

    # Then
    assert len(rates) == 1
    assert rates[0].amount == 180.0
    assert rates[0].amount_total == 180.0
    assert provider.capabilities().contract_version == provider.contract_version


def test_local_html_provider_strips_sensitive_identity_parts_and_invalid_coordinates(tmp_path) -> None:
    # Given
    page = tmp_path / "hotel.html"
    page.write_text(
        """
        <script type="application/ld+json">
        {
          "@type": "Hotel",
          "@id": "https://person:password@example.test/hotels/seguro?token=secret-marker#private",
          "name": "Hotel Privado",
          "address": {"addressLocality": "Sevilla", "addressCountry": "ES"},
          "geo": {"latitude": "Infinity", "longitude": "181"}
        }
        </script>
        """,
        encoding="utf-8",
    )
    provider = LocalHtmlHotelProviderAdapter(
        fixture_path=str(page),
        check_in=date(2026, 9, 10),
        check_out=date(2026, 9, 12),
    )

    # When
    hotel = provider.fetch_hotels()[0]

    # Then
    assert hotel.provider_hotel_id.startswith("https://example.test/hotels/seguro#local-html-")
    assert "secret-marker" not in hotel.provider_hotel_id
    assert "person" not in hotel.provider_hotel_id
    assert hotel.raw_payload == {"source": "local_html_json_ld", "identifier": hotel.provider_hotel_id}
    assert hotel.latitude is None
    assert hotel.longitude is None


def test_local_html_provider_strips_sensitive_offer_identity_parts(tmp_path) -> None:
    # Given
    page = tmp_path / "hotel.html"
    page.write_text(
        """
        <script type="application/ld+json">
        {
          "@type": "Hotel",
          "@id": "hotel-seguro",
          "name": "Hotel Seguro",
          "address": {"addressLocality": "Sevilla", "addressCountry": "ES"},
          "offers": {
            "@id": "https://person:password@example.test/offers/segura?token=secret-marker#private",
            "price": "120.00",
            "priceCurrency": "EUR",
            "description": "Total con cancelaciÃ³n",
            "priceSpecification": {"priceType": "total"}
          }
        }
        </script>
        """,
        encoding="utf-8",
    )
    provider = LocalHtmlHotelProviderAdapter(
        fixture_path=str(page),
        check_in=date(2026, 9, 10),
        check_out=date(2026, 9, 12),
    )

    # When
    rate = provider.fetch_hotels()[0].rates[0]

    # Then
    assert rate.provider_offer_id.startswith("https://example.test/offers/segura#local-html-")
    assert "secret-marker" not in rate.provider_offer_id


def test_local_html_provider_keeps_distinct_sanitized_url_identities(tmp_path) -> None:
    # Given
    page = tmp_path / "hotel.html"
    page.write_text(
        """
        <script type="application/ld+json">
        [
          {"@type": "Hotel", "@id": "https://example.test/hotel?id=one", "name": "Hotel Uno",
           "address": {"addressLocality": "Madrid", "addressCountry": "ES"}},
          {"@type": "Hotel", "@id": "https://example.test/hotel?id=two", "name": "Hotel Dos",
           "address": {"addressLocality": "Madrid", "addressCountry": "ES"}}
        ]
        </script>
        """,
        encoding="utf-8",
    )
    provider = LocalHtmlHotelProviderAdapter(
        fixture_path=str(page),
        check_in=date(2026, 9, 10),
        check_out=date(2026, 9, 12),
    )

    # When
    identifiers = [hotel.provider_hotel_id for hotel in provider.fetch_hotels()]

    # Then
    assert len(identifiers) == 2
    assert len(set(identifiers)) == 2
    assert all("?" not in identifier for identifier in identifiers)


def test_local_html_provider_preserves_clean_urls_and_distinguishes_long_opaque_ids(tmp_path) -> None:
    # Given
    page = tmp_path / "hotel.html"
    long_identifier = "relative-" + "x" * 160
    page.write_text(
        f"""
        <script type="application/ld+json">
        [
          {{"@type": "Hotel", "@id": "https://EXAMPLE.test/hotel", "name": "Hotel Uno",
           "address": {{"addressLocality": "Madrid", "addressCountry": "ES"}}}},
          {{"@type": "Hotel", "@id": "{long_identifier}", "name": "Hotel Dos",
           "address": {{"addressLocality": "Madrid", "addressCountry": "ES"}}}}
        ]
        </script>
        """,
        encoding="utf-8",
    )
    provider = LocalHtmlHotelProviderAdapter(
        fixture_path=str(page),
        check_in=date(2026, 9, 10),
        check_out=date(2026, 9, 12),
    )

    # When
    identifiers = [hotel.provider_hotel_id for hotel in provider.fetch_hotels()]

    # Then
    assert identifiers[0] == "https://EXAMPLE.test/hotel"
    assert identifiers[1].startswith("local-html-")
    assert identifiers[0] != identifiers[1]


def test_local_html_provider_safely_ignores_invalid_bytes_and_deep_json_ld(tmp_path) -> None:
    # Given
    page = tmp_path / "hotel.html"
    provider = LocalHtmlHotelProviderAdapter(
        fixture_path=str(page),
        check_in=date(2026, 9, 10),
        check_out=date(2026, 9, 12),
    )

    # When
    page.write_bytes(b"\xff<script type=\"application/ld+json\">{broken}</script>")
    invalid_bytes_result = provider.fetch_hotels()
    deeply_nested = "[" * 2_100 + "]" * 2_100
    page.write_text(
        f'<script type="application/ld+json">{{"@type":"Hotel","name":"Profundo","address":{{"addressLocality":"Madrid","addressCountry":"ES"}},"nested":{deeply_nested}}}</script>',
        encoding="utf-8",
    )
    deep_json_result = provider.fetch_hotels()

    # Then
    assert invalid_bytes_result == []
    assert deep_json_result == []


def test_local_html_provider_is_enabled_without_external_permission(monkeypatch) -> None:
    # Given
    monkeypatch.setenv("HOTEL_PROFILE", "local_fixture")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "local_scrape")
    monkeypatch.setenv("HOTEL_LOCAL_SCRAPE_CHECK_IN", "2026-09-10")
    monkeypatch.setenv("HOTEL_LOCAL_SCRAPE_CHECK_OUT", "2026-09-12")
    monkeypatch.setenv("HOTEL_LOCAL_SCRAPE_GUESTS", "2")
    monkeypatch.delenv("HOTEL_LOCAL_SCRAPE_PATH", raising=False)

    # When
    activation = resolve_hotel_activation(operation="ingestion")
    provider = resolve_hotel_provider()

    # Then
    assert activation.provider_external is False
    assert activation.external_calls_allowed is True
    assert provider.provider_id == "local_scrape"
    assert provider.is_enabled() is True
