from app.api.v1.search import _filter_ui_warning_codes, _normalize_warning_code, _normalize_warning_codes


def test_normalize_warning_code_maps_legacy_partial_aliases() -> None:
    assert _normalize_warning_code("provider_timeout_parcial") == "provider_timeout_partial"
    assert _normalize_warning_code("ryanair_unavailable_parcial") == "ryanair_unavailable_partial"
    assert _normalize_warning_code("ryanair_availability_failed_partial") == "ryanair_availability_failed_partial"


def test_normalize_warning_codes_dedupes_after_alias_mapping() -> None:
    normalized = _normalize_warning_codes(
        [
            "ryanair_unavailable_parcial",
            "ryanair_unavailable_partial",
            "provider_timeout_parcial",
            "provider_timeout_partial",
            "rescue_mode_applied",
        ]
    )
    assert normalized == [
        "ryanair_unavailable_partial",
        "provider_timeout_partial",
        "rescue_mode_applied",
    ]


def test_filter_ui_warning_codes_keeps_only_provider_critical_and_partial() -> None:
    filtered = _filter_ui_warning_codes(
        [
            "ryanair_unavailable_parcial",
            "provider_timeout_parcial",
            "ryanair_provider_unavailable_total",
            "rescue_mode_applied",
            "limite_combinaciones_alternativas",
            "result_out_of_scope_discarded",
        ]
    )
    assert filtered == [
        "ryanair_unavailable_partial",
        "provider_timeout_partial",
        "ryanair_provider_unavailable_total",
    ]
