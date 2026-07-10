from app.services.provider_health_stats import (
    ProviderHealthSample,
    record_provider_health_sample,
    reset_provider_health_stats_for_tests,
    snapshot_provider_health,
)


def test_provider_health_stats_aggregate_provider_degradation_signals() -> None:
    reset_provider_health_stats_for_tests()

    record_provider_health_sample(
        ProviderHealthSample(
            provider_id="ryanair-public",
            elapsed_ms=120,
            flights_count=2,
            warning_codes=(),
            succeeded=True,
        )
    )
    record_provider_health_sample(
        ProviderHealthSample(
            provider_id="ryanair-public",
            elapsed_ms=80,
            flights_count=0,
            warning_codes=("provider_timeout_partial",),
            succeeded=False,
        )
    )
    record_provider_health_sample(
        ProviderHealthSample(
            provider_id="vueling",
            elapsed_ms=40,
            flights_count=0,
            warning_codes=("provider_waf_challenge", "invalid_price"),
            succeeded=False,
        )
    )
    record_provider_health_sample(
        ProviderHealthSample(
            provider_id="vueling",
            elapsed_ms=60,
            flights_count=0,
            warning_codes=("no_results",),
            succeeded=True,
        )
    )

    snapshots = {item.provider_id: item for item in snapshot_provider_health()}

    assert snapshots["ryanair-public"].calls == 2
    assert snapshots["ryanair-public"].successes == 1
    assert snapshots["ryanair-public"].timeouts == 1
    assert snapshots["ryanair-public"].average_latency_ms == 100.0
    assert snapshots["vueling"].calls == 2
    assert snapshots["vueling"].waf_challenges == 1
    assert snapshots["vueling"].invalid_prices == 1
    assert snapshots["vueling"].no_results == 1
    assert snapshots["vueling"].average_latency_ms == 50.0
