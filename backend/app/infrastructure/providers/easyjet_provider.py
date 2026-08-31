from __future__ import annotations

from collections.abc import Mapping
import os
import random
import time
from typing import Any, Final

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException

from app.domain.entities import ProviderFetchResult, ProviderSourceFetchError, ProviderWarning
from app.infrastructure.providers.base import FlightProvider
from app.infrastructure.providers.easyjet_flight_connections import (
    build_flight_connections_params,
    extract_flight_connections_flights,
)
from app.infrastructure.providers.easyjet_public_availability import (
    JsonValue,
    build_public_availability_params,
    extract_public_availability_flights,
)
from app.infrastructure.providers._browser_warmup import (
    warm_session_with_browser,
)
from app.infrastructure.providers._captcha import detect_captcha_kind
from app.infrastructure.providers._easyjet_provider_support import (
    EASYJET_WAF_RULES,
    EasyJetSearch,
    flight_connections_headers,
    normalize_search,
    public_availability_headers,
    raise_invalid_json,
    raise_provider_unavailable,
    raise_waf_challenge,
    request_with_optional_browser,
    to_flight_connections_search,
    to_public_availability_search,
    warmup_headers,
)
from app.infrastructure.providers._session_factory import build_session_kwargs

curl_requests: Any | None
CurlRequestsError: type[Exception]
try:
    from curl_cffi import requests as imported_curl_requests
    from curl_cffi.requests.errors import RequestsError as imported_curl_requests_error
except ImportError:
    curl_requests = None
    CurlRequestsError = RequestException
else:
    curl_requests = imported_curl_requests
    CurlRequestsError = imported_curl_requests_error

RequestsError = CurlRequestsError

_DEFAULT_BASE_URL: Final = "https://www.easyjet.com"
_DEFAULT_FLIGHT_CONNECTIONS_URL: Final = "https://flightconnections.easyjet.com"
_DEFAULT_LANGUAGE_CODE: Final = "EN"
_DEFAULT_RESIDENCY: Final = "ES"
_DEFAULT_IMPERSONATE: Final = "chrome131"
_IMPERSONATE_ENV_VAR: Final = "EASYJET_IMPERSONATE"
_PROVIDER_POOL_SIZE: Final = 32
_EASYJET_WAF_RULES = EASYJET_WAF_RULES


class EasyJetProvider(FlightProvider):
    provider_id = "easyjet"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        language_code: str | None = None,
        impersonate: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("EASYJET_BASE_URL") or _DEFAULT_BASE_URL).strip().rstrip("/")
        self.flight_connections_url = os.getenv(
            "EASYJET_FLIGHT_CONNECTIONS_URL"
        ) or _DEFAULT_FLIGHT_CONNECTIONS_URL
        self.flight_connections_url = self.flight_connections_url.strip().rstrip("/")
        self.flight_connections_bypass_secret = (
            os.getenv("EASYJET_FLIGHT_CONNECTIONS_BYPASS_SECRET")
            or os.getenv("DATADOME_BYPASS_SECRET")
            or ""
        ).strip()
        self.language_code = (
            language_code or os.getenv("EASYJET_LANGUAGE_CODE") or _DEFAULT_LANGUAGE_CODE
        ).strip().upper()
        self.residency = (os.getenv("EASYJET_RESIDENCY") or _DEFAULT_RESIDENCY).strip().upper()
        impersonate_version = (
            impersonate or os.getenv(_IMPERSONATE_ENV_VAR) or _DEFAULT_IMPERSONATE
        ).strip() or _DEFAULT_IMPERSONATE
        self._session: Any
        try:
            if curl_requests is None:
                raise TypeError("curl_cffi_unavailable")
            session_kwargs = build_session_kwargs(
                impersonate_env=_IMPERSONATE_ENV_VAR,
                extra_fp_env="EASYJET_EXTRA_FP",
                proxy_env="EASYJET_PROXY",
                ja3_env="EASYJET_JA3",
            )
            session_kwargs["impersonate"] = impersonate_version
            self._session = curl_requests.Session(**session_kwargs)
        except TypeError:
            # stdlib ``requests`` (test doubles / curl_cffi import failure):
            # drop curl_cffi-only kwargs and fall back to a vanilla pool.
            self._session = requests.Session()
            adapter = HTTPAdapter(pool_connections=_PROVIDER_POOL_SIZE, pool_maxsize=_PROVIDER_POOL_SIZE)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
        self._warmed = False

    def is_enabled(self) -> bool:
        return bool(self.base_url and self.flight_connections_url and self.language_code and self.residency)

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        search = normalize_search(origin, destination, travel_date, currency)
        self._warm_session(self.base_url, referer_path=f"/{self.language_code.lower()}/", kind="marketing")
        source_error: Exception | None = None
        try:
            payload = self._fetch_public_availability(search, timeout_ms=timeout_ms)
            flights = extract_public_availability_flights(
                payload,
                to_public_availability_search(
                    search,
                    language_code=self.language_code,
                    base_url=self.base_url,
                ),
            )
        except ProviderSourceFetchError:
            # Captcha / source-specific failures: propagate unchanged so the
            # orchestrator sees the rich captcha warning_codes the helper
            # produced. The flight connections fallback would just hit the
            # same WAF on the same IP, so don't fall through.
            raise
        except (CurlRequestsError, RequestException, ValueError) as exc:
            source_error = exc
            flights = []

        if not flights:
            self._warm_session(self.flight_connections_url, referer_path=f"/{self.language_code.lower()}/", kind="flightconnections")
            try:
                connections_payload = self._fetch_flight_connections(search, timeout_ms=timeout_ms)
                flights = extract_flight_connections_flights(
                    connections_payload,
                    to_flight_connections_search(
                        search,
                        language_code=self.language_code,
                        residency=self.residency,
                        base_url=self.flight_connections_url,
                    ),
                )
            except ProviderSourceFetchError as exc:
                if any(
                    code.startswith("easyjet_flight_connections_captcha_")
                    for code in exc.warning_codes
                ):
                    raise
                source_error = exc
            except (CurlRequestsError, RequestException, ValueError) as exc:
                source_error = exc

        if source_error is not None and not flights:
            raise_provider_unavailable(search, source_error)

        warnings_structured: list[ProviderWarning] = []
        if not flights:
            warnings_structured.append(
                ProviderWarning(code="provider_empty_result", provider=self.provider_id, severity="info")
            )
        return ProviderFetchResult(flights=flights, warnings=[], warnings_structured=warnings_structured)

    def _fetch_public_availability(self, search: EasyJetSearch, *, timeout_ms: int) -> Mapping[str, JsonValue]:
        time.sleep(random.uniform(0.1, 0.4))
        response = request_with_optional_browser(
            self._session,
            "GET",
            f"{self.base_url}/ejavailability/api/v16/availability/query",
            params=build_public_availability_params(
                to_public_availability_search(
                    search,
                    language_code=self.language_code,
                    base_url=self.base_url,
                )
            ),
            headers=public_availability_headers(self.base_url, self.language_code, self.residency),
            timeout_ms=timeout_ms,
            warmup_url=self.base_url,
            warmup_referer_path=f"/{self.language_code.lower()}/",
        )
        captcha_kind = detect_captcha_kind(response, rules=EASYJET_WAF_RULES)
        if captcha_kind:
            raise_waf_challenge(
                search=search,
                captcha_kind=captcha_kind,
                warning_prefix="easyjet_provider_captcha",
                message_subject="easyJet",
            )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise_invalid_json(exc)
        return payload if isinstance(payload, dict) else {}

    def _fetch_flight_connections(self, search: EasyJetSearch, *, timeout_ms: int) -> Mapping[str, JsonValue]:
        flight_connections_search = to_flight_connections_search(
            search,
            language_code=self.language_code,
            residency=self.residency,
            base_url=self.flight_connections_url,
        )
        time.sleep(random.uniform(0.1, 0.4))
        headers = flight_connections_headers(
            self.flight_connections_url,
            self.language_code,
            self.residency,
            self.flight_connections_bypass_secret,
        )
        response = request_with_optional_browser(
            self._session,
            "POST",
            f"{self.flight_connections_url}/api/graphql",
            json_body=build_flight_connections_params(flight_connections_search),
            headers=headers,
            timeout_ms=timeout_ms,
            warmup_url=self.flight_connections_url,
            warmup_referer_path=f"/{self.language_code.lower()}/",
        )
        captcha_kind = detect_captcha_kind(response, rules=EASYJET_WAF_RULES)
        if captcha_kind:
            raise_waf_challenge(
                search=search,
                captcha_kind=captcha_kind,
                warning_prefix="easyjet_flight_connections_captcha",
                message_subject="easyJet Flight Connections",
            )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def _warm_session(self, base_url: str, *, referer_path: str = "", kind: str = "marketing") -> None:
        marker = f"_warmed_{kind}"
        if getattr(self, marker, False):
            return
        session_get = getattr(self._session, "get", None)
        if session_get is None:
            # Test doubles / non-curl-cffi fallback: skip without throwing.
            setattr(self, marker, True)
            return
        try:
            time.sleep(random.uniform(0.05, 0.2))
            session_get(
                f"{base_url}{referer_path}",
                timeout=2.0,
                headers=warmup_headers(self.language_code, self.residency),
            )
        except Exception:
            pass
        setattr(self, marker, True)
        self._browser_warmup(base_url, referer_path=referer_path, kind=kind)

    def _browser_warmup(self, base_url: str, *, referer_path: str, kind: str = "marketing") -> None:
        browser_marker = f"_warmed_browser_{kind}"
        if getattr(self, browser_marker, False):
            return
        if warm_session_with_browser(
            self._session,
            env_var="EASYJET_USE_BROWSER_WARMUP",
            base_url=base_url,
            referer_path=referer_path,
        ):
            setattr(self, browser_marker, True)
