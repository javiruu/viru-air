from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
import random
import time
from typing import Any, Final

try:
    from curl_cffi import requests
    from curl_cffi.requests.errors import RequestsError
except ImportError:
    import requests
    from requests.exceptions import RequestException as RequestsError
from requests.adapters import HTTPAdapter

from app.domain.entities import ProviderFetchResult, ProviderSourceFetchError, ProviderWarning
from app.infrastructure.providers.base import FlightProvider
from app.infrastructure.providers.easyjet_flight_connections import (
    EasyJetFlightConnectionsSearch,
    build_flight_connections_params,
    extract_flight_connections_flights,
)
from app.infrastructure.providers.easyjet_public_availability import (
    EasyJetPublicAvailabilitySearch,
    JsonValue,
    build_public_availability_params,
    extract_public_availability_flights,
)
from app.infrastructure.providers._captcha import WafRule, detect_captcha_kind

_DEFAULT_BASE_URL: Final = "https://www.easyjet.com"
_DEFAULT_FLIGHT_CONNECTIONS_URL: Final = "https://flightconnections.easyjet.com"
_DEFAULT_LANGUAGE_CODE: Final = "EN"
_DEFAULT_RESIDENCY: Final = "ES"
_DEFAULT_IMPERSONATE: Final = "chrome131"
_IMPERSONATE_ENV_VAR: Final = "EASYJET_IMPERSONATE"
_CHROME131_UA_SIG: Final = '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"'
_PROVIDER_POOL_SIZE: Final = 32


@dataclass(frozen=True, slots=True)
class _EasyJetSearch:
    origin: str
    destination: str
    travel_date: str
    currency: str


# Rules specific to easyJet's WAF mix (Datadome + Dohop, with Akamai
# fallback). Order: specific captcha/HTML first, generic deny last.
#
# `datadome_captcha` fires on either path: a Datadome-tagged 403 *or* an HTML
# challenge page that mentions Datadome markers. Datadome cookies are per
# domain, so a fresh cookie-less request is frequently served a JS-driven
# challenge page (HTML body, status 200) rather than a 403; both branches
# look for the same DOM strings.
_EASYJET_WAF_RULES: Final[dict[str, WafRule]] = {
    "datadome_captcha": lambda status, text: (
        status == 403
        and ("datadome" in text or "dd_block" in text or "captcha-delivery.com" in text)
    )
    or (
        "<html" in text
        and (
            "datadome" in text
            or "dd_block" in text
            or "captcha" in text
            or "challenge" in text
        )
    ),
    "akamai_blocked": lambda status, text: status == 403
    and ("access denied" in text or "request rejected" in text),
}



class EasyJetProvider(FlightProvider):
    provider_id = "easyjet"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        language_code: str | None = None,
        impersonate: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("EASYJET_BASE_URL", _DEFAULT_BASE_URL)).strip().rstrip("/")
        self.flight_connections_url = os.getenv(
            "EASYJET_FLIGHT_CONNECTIONS_URL", _DEFAULT_FLIGHT_CONNECTIONS_URL
        ).strip().rstrip("/")
        self.flight_connections_bypass_secret = (
            os.getenv("EASYJET_FLIGHT_CONNECTIONS_BYPASS_SECRET")
            or os.getenv("DATADOME_BYPASS_SECRET", "")
        ).strip()
        self.language_code = (
            language_code or os.getenv("EASYJET_LANGUAGE_CODE", _DEFAULT_LANGUAGE_CODE)
        ).strip().upper()
        self.residency = os.getenv("EASYJET_RESIDENCY", _DEFAULT_RESIDENCY).strip().upper()
        impersonate_version = (
            impersonate or os.getenv(_IMPERSONATE_ENV_VAR, _DEFAULT_IMPERSONATE)
        ).strip() or _DEFAULT_IMPERSONATE
        try:
            self._session = requests.Session(impersonate=impersonate_version)
        except TypeError:
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
        search = _EasyJetSearch(
            origin=origin.upper().strip(),
            destination=destination.upper().strip(),
            travel_date=travel_date,
            currency=currency.upper().strip(),
        )
        # Warm up BOTH domains: easyjet.com for the public availability endpoint
        # and flightconnections.easyjet.com (Dohop) for the GraphQL fallback.
        # Datadome cookies are domain-scoped, so each endpoint wants its own
        # preflight hit before its real API call.
        self._warm_session(self.base_url, referer_path=f"/{self.language_code.lower()}/", kind="marketing")
        source_error: Exception | None = None
        try:
            payload = self._fetch_public_availability(search, timeout_ms=timeout_ms)
            flights = extract_public_availability_flights(payload, self._to_public_availability_search(search))
        except ProviderSourceFetchError:
            # Captcha / source-specific failures: propagate unchanged so the
            # orchestrator sees the rich captcha warning_codes the helper
            # produced. The flight connections fallback would just hit the
            # same WAF on the same IP, so don't fall through.
            raise
        except (RequestsError, ValueError) as exc:
            source_error = exc
            flights = []

        if not flights:
            self._warm_session(self.flight_connections_url, referer_path=f"/{self.language_code.lower()}/search", kind="flightconnections")
            try:
                connections_payload = self._fetch_flight_connections(search, timeout_ms=timeout_ms)
                flights = extract_flight_connections_flights(
                    connections_payload, self._to_flight_connections_search(search)
                )
            except ProviderSourceFetchError:
                raise
            except (RequestsError, ValueError) as exc:
                source_error = exc

        if source_error is not None and not flights:
            raise ProviderSourceFetchError(
                warning_codes=["easyjet_provider_unavailable_total", "provider_total_outage"],
                message=f"easyJet provider unavailable for {search.origin}->{search.destination} on {search.travel_date}",
                provider_id=self.provider_id,
                severity="error",
            ) from source_error

        warnings_structured: list[ProviderWarning] = []
        if not flights:
            warnings_structured.append(
                ProviderWarning(code="provider_empty_result", provider=self.provider_id, severity="info")
            )
        return ProviderFetchResult(flights=flights, warnings=[], warnings_structured=warnings_structured)

    def _fetch_public_availability(self, search: _EasyJetSearch, *, timeout_ms: int) -> Mapping[str, JsonValue]:
        time.sleep(random.uniform(0.1, 0.4))
        # NOTE: keep headers minimal. curl_cffi's impersonation pairs a realistic
        # Chrome UA, sec-ch-* and sec-fetch-* with the matching TLS fingerprint;
        # overriding those breaks the pairing (Datadome flagged the barebones
        # "Mozilla/5.0" we used before this fix as a confident bot signature).
        response = self._session.get(
            f"{self.base_url}/ejavailability/api/v16/availability/query",
            params=build_public_availability_params(self._to_public_availability_search(search)),
            timeout=max(2.0, timeout_ms / 1000),
            headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": f"{self.language_code.lower()}-{self.residency},{self.language_code.lower()};q=0.9,en;q=0.8",
                "Origin": self.base_url,
                "Referer": f"{self.base_url}/{self.language_code.lower()}/buy/flights",
                "sec-ch-ua": _CHROME131_UA_SIG,
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "sec-fetch-dest": "empty",
            },
        )
        captcha_kind = detect_captcha_kind(response, rules=_EASYJET_WAF_RULES)
        if captcha_kind:
            raise ProviderSourceFetchError(
                warning_codes=[
                    f"easyjet_provider_captcha_{captcha_kind}",
                    "easyjet_provider_unavailable_total",
                    "provider_total_outage",
                ],
                message=f"easyJet WAF returned a bot challenge ({captcha_kind}) for {search.origin}->{search.destination} on {search.travel_date}",
                provider_id=self.provider_id,
                severity="error",
                meta={"reason": captcha_kind},
            )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderSourceFetchError(
                warning_codes=["easyjet_provider_unavailable_total", "provider_total_outage"],
                message="easyJet provider returned a non-JSON response",
                provider_id=self.provider_id,
                severity="error",
                meta={"reason": "invalid_json"},
            ) from exc
        return payload if isinstance(payload, dict) else {}

    def _to_public_availability_search(self, search: _EasyJetSearch) -> EasyJetPublicAvailabilitySearch:
        return EasyJetPublicAvailabilitySearch(
            origin=search.origin,
            destination=search.destination,
            travel_date=search.travel_date,
            currency=search.currency,
            language=self.language_code,
            base_url=self.base_url,
        )

    def _fetch_flight_connections(self, search: _EasyJetSearch, *, timeout_ms: int) -> Mapping[str, JsonValue]:
        flight_connections_search = self._to_flight_connections_search(search)
        time.sleep(random.uniform(0.1, 0.4))
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": f"{self.language_code.lower()}-{self.residency},{self.language_code.lower()};q=0.9,en;q=0.8",
            "Origin": self.flight_connections_url,
            "Referer": f"{self.flight_connections_url}/{self.language_code.lower()}/search",
            "sec-ch-ua": _CHROME131_UA_SIG,
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-fetch-dest": "empty",
            "content-type": "application/json",
        }
        if self.flight_connections_bypass_secret:
            headers["X-Dohop-Bypass"] = self.flight_connections_bypass_secret
        # Switched from GET (params-as-query) to POST (json body): a 2KB GraphQL
        # query + JSON-encoded variables sent as URL params trips Dohop's WAF on
        # URI length / pattern rules. POST keeps the same payload contract but
        # inside the body where WAFs handle it gracefully.
        response = self._session.post(
            f"{self.flight_connections_url}/api/graphql",
            json=build_flight_connections_params(flight_connections_search),
            timeout=max(2.0, timeout_ms / 1000),
            headers=headers,
        )
        captcha_kind = detect_captcha_kind(response, rules=_EASYJET_WAF_RULES)
        if captcha_kind:
            raise ProviderSourceFetchError(
                warning_codes=[
                    f"easyjet_flight_connections_captcha_{captcha_kind}",
                    "easyjet_provider_unavailable_total",
                    "provider_total_outage",
                ],
                message=f"easyJet Flight Connections WAF returned a bot challenge ({captcha_kind}) for {search.origin}->{search.destination} on {search.travel_date}",
                provider_id=self.provider_id,
                severity="error",
                meta={"reason": captcha_kind},
            )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def _warm_session(self, base_url: str, *, referer_path: str = "", kind: str = "marketing") -> None:
        """Best-effort warmup to acquire Datadome cookies.

        Each domain has its own Datadome set-up, so we mark the session warmed
        per-kind. Errors are swallowed: failed warmups are silent, and the
        follow-up availability / GraphQL call still surfaces the real outcome
        (with a captcha_kind label if Datadome returns a challenge).
        """
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
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": f"{self.language_code.lower()}-{self.residency},{self.language_code.lower()};q=0.9,en;q=0.8",
                    "sec-ch-ua": _CHROME131_UA_SIG,
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-fetch-mode": "navigate",
                    "sec-fetch-site": "none",
                    "sec-fetch-dest": "document",
                    "sec-fetch-user": "?1",
                    "upgrade-insecure-requests": "1",
                },
            )
        except Exception:
            pass
        setattr(self, marker, True)
        if os.getenv("EASYJET_USE_BROWSER_WARMUP") in {"1", "true", "yes", "on"}:
            self._browser_warmup(base_url, referer_path=referer_path, kind=kind)

    def _browser_warmup(self, base_url: str, *, referer_path: str, kind: str = "marketing") -> None:
        """Opt-in Playwright warmup layered on top of the curl warmup.

        Mirror of ``IberiaProvider._browser_warmup`` with a ``kind`` discriminator
        (Datadome cookies are per-domain, so each warm site needs its own pass).
        Self-gated on ``EASYJET_USE_BROWSER_WARMUP`` so direct callers (tests,
        future code paths) are a no-op when the operator hasn't enabled the
        headless path. Failures (Playwright missing, Chromium binary missing,
        target unreachable) are swallowed so the curl warmup and the eventual
        availability call keep working with whatever they have. Cookies
        harvested from the headless navigation are merged into the curl_cffi
        session's jar.
        """
        if os.getenv("EASYJET_USE_BROWSER_WARMUP") not in {"1", "true", "yes", "on"}:
            return
        # Idempotent on the per-kind marker so a future direct caller can't
        # respawn Playwright per request.
        browser_marker = f"_warmed_browser_{kind}"
        if getattr(self, browser_marker, False):
            return
        try:
            from app.infrastructure.providers._browser_warmup import (
                harvest_cookies_with_browser,
                merge_cookies_into_session,
            )
        except ImportError:
            return
        cookies = harvest_cookies_with_browser(base_url, referer_path=referer_path)
        merge_cookies_into_session(self._session, cookies)
        setattr(self, browser_marker, True)

    def _to_flight_connections_search(self, search: _EasyJetSearch) -> EasyJetFlightConnectionsSearch:
        return EasyJetFlightConnectionsSearch(
            origin=search.origin,
            destination=search.destination,
            travel_date=search.travel_date,
            currency=search.currency,
            language=self.language_code,
            residency=self.residency,
            base_url=self.flight_connections_url,
        )
