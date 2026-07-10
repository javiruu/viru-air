import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities import ProviderFetchResult
from app.infrastructure.db.models import Base
from app.services.quick_search_cache_service import (
    get_fresh_negative_cache_entry,
    resolve_negative_cache_result,
    set_negative_cache_entry,
)
from app.services.quick_search_negative_cache_write_policy import resolve_negative_cache_write_policy


@pytest.fixture()
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize(
    ("reason", "min_ttl", "max_ttl", "freshness_status", "warnings"),
    [
        ("no_results", 3600, 3600, "negative_fresh", []),
        ("invalid_price", 900, 900, "negative_fresh", []),
        ("unsupported_route", 43200, 43200, "negative_fresh", []),
        ("provider_timeout", 300, 330, "provider_error_fresh", ["provider_timeout_partial"]),
        ("provider_total_outage", 180, 210, "provider_error_fresh", ["provider_total_outage"]),
        ("provider_partial_degraded", 600, 630, "provider_error_fresh", ["provider_error_partial"]),
        ("provider_waf_challenge", 120, 150, "provider_error_fresh", ["provider_waf_challenge"]),
        ("provider_schema_changed", 300, 330, "provider_error_fresh", ["provider_schema_changed"]),
    ],
)
def test_negative_cache_reason_policy_sets_professional_ttl(
    db: Session,
    reason: str,
    min_ttl: int,
    max_ttl: int,
    freshness_status: str,
    warnings: list[str],
) -> None:
    entry = set_negative_cache_entry(
        db,
        negative_fingerprint=f"qsn_{reason}",
        scope="route_date_provider",
        reason=reason,
        provider="multi",
        canonical_request_json="{}",
    )

    ttl_seconds = int((entry.expires_at - entry.observed_at).total_seconds())
    result = resolve_negative_cache_result(entry)
    assert min_ttl <= ttl_seconds <= max_ttl
    assert entry.freshness_status == freshness_status
    assert result.flights == []
    assert result.warnings == warnings


def test_negative_cache_hit_increments_counter_and_stale_entry_misses(db: Session) -> None:
    fingerprint = "qsn_stale_contract"
    entry = set_negative_cache_entry(
        db,
        negative_fingerprint=fingerprint,
        scope="route_date_provider",
        reason="no_results",
        provider="multi",
        canonical_request_json="{}",
    )
    fresh_hit = get_fresh_negative_cache_entry(db, negative_fingerprint=fingerprint)
    assert fresh_hit is not None
    assert fresh_hit.hit_count == 1

    entry.expires_at = dt.datetime(2026, 1, 1, 0, 0)
    db.commit()
    assert get_fresh_negative_cache_entry(db, negative_fingerprint=fingerprint) is None


@pytest.mark.parametrize(
    ("warnings", "reason"),
    [
        ([], "no_results"),
        (["provider_timeout_partial"], "provider_timeout"),
        (["provider_total_outage"], "provider_total_outage"),
        (["provider_error_partial"], "provider_partial_degraded"),
        (["ryanair_fares_failed"], "provider_partial_degraded"),
        (["invalid_price"], "invalid_price"),
        (["iberia_provider_captcha_akamai_blocked"], "provider_waf_challenge"),
        (["easyjet_flight_connections_captcha_datadome_captcha"], "provider_waf_challenge"),
        (["provider_schema_changed"], "provider_schema_changed"),
    ],
)
def test_quick_search_negative_write_policy_uses_minimum_reason_codes(
    warnings: list[str],
    reason: str,
) -> None:
    result = ProviderFetchResult(flights=[], warnings=warnings)
    resolved_reason, _retry_after_at = resolve_negative_cache_write_policy(result)
    assert resolved_reason == reason


@pytest.mark.parametrize(
    "warnings",
    [
        ["provider_total_outage", "iberia_provider_captcha_akamai_blocked"],
        ["provider_error_partial", "provider_schema_changed"],
    ],
)
def test_dangerous_provider_errors_are_not_written_as_empty_routes(warnings: list[str]) -> None:
    result = ProviderFetchResult(flights=[], warnings=warnings)
    resolved_reason, retry_after_at = resolve_negative_cache_write_policy(result)

    assert resolved_reason != "no_results"
    assert retry_after_at is not None
