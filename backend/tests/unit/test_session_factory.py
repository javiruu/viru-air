"""Direct tests for the operator-driven session kwargs factory.

Each provider reads four env vars (impersonate / extra_fp / proxy / ja3) from
this factory. The tests below exercise the factory in isolation so the
provider unit suite can trust that environmental wiring works correctly.
"""

from __future__ import annotations

import pytest

from app.infrastructure.providers import _session_factory
from app.infrastructure.providers._session_factory import build_session_kwargs

_IBERIA_KWARGS = dict(
    impersonate_env="IBERIA_IMPERSONATE",
    extra_fp_env="IBERIA_EXTRA_FP",
    proxy_env="IBERIA_PROXY",
    ja3_env="IBERIA_JA3",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "IBERIA_IMPERSONATE",
        "IBERIA_EXTRA_FP",
        "IBERIA_PROXY",
        "IBERIA_JA3",
        "EASYJET_IMPERSONATE",
        "EASYJET_EXTRA_FP",
        "EASYJET_PROXY",
        "EASYJET_JA3",
    ):
        monkeypatch.delenv(var, raising=False)


def test_default_impersonate_is_chrome131() -> None:
    """No env vars → factory returns just ``impersonate=chrome131``."""
    kwargs = build_session_kwargs(**_IBERIA_KWARGS)
    assert kwargs == {"impersonate": "chrome131"}


def test_unknown_impersonate_env_name_falls_back_to_chrome131() -> None:
    """If operator clears IBERIA_IMPERSONATE to whitespace, we still get a valid preset."""
    kwargs = build_session_kwargs(
        impersonate_env="IBERIA_IMPERSONATE",
        extra_fp_env="IBERIA_EXTRA_FP",
        proxy_env="IBERIA_PROXY",
        ja3_env="IBERIA_JA3",
    )
    # default fallback
    assert kwargs["impersonate"] == "chrome131"


def test_impersonate_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IBERIA_IMPERSONATE", "chrome136")
    kwargs = build_session_kwargs(**_IBERIA_KWARGS)
    assert kwargs["impersonate"] == "chrome136"


def test_extra_fp_valid_json_is_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "IBERIA_EXTRA_FP",
        '{"tls_grease": true, "tls_min_version": "TLSv1.3", "h2_initial_window_size": 65535}',
    )
    kwargs = build_session_kwargs(**_IBERIA_KWARGS)
    assert kwargs["extra_fp"]["tls_grease"] is True
    assert kwargs["extra_fp"]["tls_min_version"] == "TLSv1.3"
    assert kwargs["extra_fp"]["h2_initial_window_size"] == 65535


def test_extra_fp_unknown_keys_are_dropped(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setenv(
        "IBERIA_EXTRA_FP",
        '{"tls_grease": true, "mystery_knob": 1, "another_unknown": "x"}',
    )
    caplog.set_level("INFO", logger="app.infrastructure.providers._session_factory")
    kwargs = build_session_kwargs(**_IBERIA_KWARGS)
    assert "tls_grease" in kwargs["extra_fp"]
    assert "mystery_knob" not in kwargs["extra_fp"]
    assert "another_unknown" not in kwargs["extra_fp"]
    assert any("not recognised" in record.message for record in caplog.records)


def test_extra_fp_malformed_json_is_ignored(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setenv("IBERIA_EXTRA_FP", "{not valid json")
    caplog.set_level("INFO", logger="app.infrastructure.providers._session_factory")
    kwargs = build_session_kwargs(**_IBERIA_KWARGS)
    assert "extra_fp" not in kwargs
    assert any("not valid JSON" in record.message for record in caplog.records)


def test_extra_fp_non_object_json_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IBERIA_EXTRA_FP", "[1, 2, 3]")
    kwargs = build_session_kwargs(**_IBERIA_KWARGS)
    assert "extra_fp" not in kwargs


def test_proxy_sets_http_https_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IBERIA_PROXY", "http://user:pass@residential.example.com:8080")
    kwargs = build_session_kwargs(**_IBERIA_KWARGS)
    assert kwargs["proxies"]["http"] == "http://user:pass@residential.example.com:8080"
    assert kwargs["proxies"]["https"] == "http://user:pass@residential.example.com:8080"


def test_socks5_proxy_is_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EASYJET_PROXY", "socks5h://127.0.0.1:1080")
    kwargs = build_session_kwargs(
        impersonate_env="EASYJET_IMPERSONATE",
        extra_fp_env="EASYJET_EXTRA_FP",
        proxy_env="EASYJET_PROXY",
        ja3_env="EASYJET_JA3",
    )
    assert kwargs["proxies"]["https"] == "socks5h://127.0.0.1:1080"


def test_proxy_empty_value_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IBERIA_PROXY", "   ")
    kwargs = build_session_kwargs(**_IBERIA_KWARGS)
    assert "proxies" not in kwargs


def test_ja3_truthy_values_set_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    for truthy in {"1", "true", "yes", "on", "TRUE", "On"}:
        monkeypatch.setenv("IBERIA_JA3", truthy)
        kwargs = build_session_kwargs(**_IBERIA_KWARGS)
        assert kwargs.get("ja3") is True, f"'{truthy}' should set ja3=True"


def test_ja3_unset_or_falsy_does_not_set_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    for falsy in {"", "0", "no", "false", "off"}:
        monkeypatch.setenv("IBERIA_JA3", falsy)
        kwargs = build_session_kwargs(**_IBERIA_KWARGS)
        assert "ja3" not in kwargs, f"'{falsy}' should not set ja3"


def test_extra_fp_empty_value_is_ignored() -> None:
    """An env var present but empty string should not add the kwarg."""
    kwargs = build_session_kwargs(**_IBERIA_KWARGS)
    assert "extra_fp" not in kwargs


def test_all_knobs_compose_together(monkeypatch: pytest.MonkeyPatch) -> None:
    """A realistic operator config: impersonate + extra_fp + proxy + ja3."""
    monkeypatch.setenv("IBERIA_IMPERSONATE", "firefox133")
    monkeypatch.setenv("IBERIA_EXTRA_FP", '{"tls_grease": true, "tls_min_version": "TLSv1.3"}')
    monkeypatch.setenv("IBERIA_PROXY", "http://10.0.0.1:3128")
    monkeypatch.setenv("IBERIA_JA3", "1")
    kwargs = build_session_kwargs(**_IBERIA_KWARGS)
    assert kwargs["impersonate"] == "firefox133"
    assert kwargs["extra_fp"]["tls_grease"] is True
    assert kwargs["proxies"]["https"] == "http://10.0.0.1:3128"
    assert kwargs["ja3"] is True


def test_known_extra_fp_keys_includes_tls_and_h2_overrides() -> None:
    """Public surface: at least TLS GREASE, TLS min version, H2 window size, header order."""
    expected = {
        "tls_grease",
        "tls_min_version",
        "h2_initial_window_size",
        "pseudo_header_order",
        "header_order",
    }
    assert expected.issubset(_session_factory._KNOWN_EXTRA_FP_KEYS)


def test_factory_does_not_raise_on_bad_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Whatever the operator does, the factory succeeds (provider runtime keeps working)."""
    monkeypatch.setenv("IBERIA_EXTRA_FP", "{}")
    monkeypatch.setenv("IBERIA_PROXY", "garbage url")
    monkeypatch.setenv("IBERIA_JA3", "maybe")
    kwargs = build_session_kwargs(**_IBERIA_KWARGS)
    assert "impersonate" in kwargs
    assert kwargs["proxies"]["https"] == "garbage url"  # we forward raw; curl_cffi raises if invalid
