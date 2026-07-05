from __future__ import annotations

from collections.abc import Mapping
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
from app.infrastructure.providers.iberia_public_availability import (
    IberiaPublicAvailabilitySearch,
    build_public_availability_request,
    extract_public_availability_flights,
)

_DEFAULT_BASE_URL: Final = "https://www.iberia.com"
_DEFAULT_API_BASE_URL: Final = "https://ibisservices.iberia.com/api"
_DEFAULT_AVAILABILITY_PATH: Final = "/sse-avm/rs/v2/availability"
_DEFAULT_AUTHORIZATION: Final = "Basic aWJlcmlhX3dlYjo5ZGM4NzZjYi0xMDVkLTQ4MWItODM4Yy01NGUyNGQ3NDEwYzk="
_DEFAULT_MARKET: Final = "ES"
_DEFAULT_LANGUAGE: Final = "es"
_DEFAULT_IMPERSONATE: Final = "chrome131"
_IMPERSONATE_ENV_VAR: Final = "IBERIA_IMPERSONATE"
_CHROME131_UA_SIG: Final = '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"'
_PROVIDER_POOL_SIZE: Final = 32


class IberiaProvider(FlightProvider):
    provider_id = "iberia"

    def __init__(
        self,
        *,
        api_base_url: str | None = None,
        base_url: str | None = None,
        authorization: str | None = None,
        market: str | None = None,
        language: str | None = None,
        impersonate: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("IBERIA_BASE_URL", _DEFAULT_BASE_URL)).strip().rstrip("/")
        self.api_base_url = (
            api_base_url or os.getenv("IBERIA_API_BASE_URL", _DEFAULT_API_BASE_URL)
        ).strip().rstrip("/")
        self.availability_path = os.getenv("IBERIA_AVAILABILITY_PATH", _DEFAULT_AVAILABILITY_PATH).strip()
        self.authorization = (
            authorization or os.getenv("IBERIA_PUBLIC_AUTHORIZATION", _DEFAULT_AUTHORIZATION)
        ).strip()
        self.market = (market or os.getenv("IBERIA_MARKET", _DEFAULT_MARKET)).strip().upper()
        self.language = (language or os.getenv("IBERIA_LANGUAGE", _DEFAULT_LANGUAGE)).strip().lower()
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
        # Sessions reuse cookies across calls, so the warm-up marker sticks for
        # the lifetime of the provider (matches ThreadPoolExecutor lifespan).
        self._warmed = False

    def is_enabled(self) -> bool:
        return bool(self.base_url and self.api_base_url and self.authorization and self.market and self.language)

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        search = self._build_search(origin, destination, travel_date, currency)
        self._warm_session(self.base_url, referer_path="/")
        try:
            payload = self._fetch_public_availability(search, timeout_ms=timeout_ms)
        except (RequestsError, ValueError, ProviderSourceFetchError) as exc:
            raise ProviderSourceFetchError(
                warning_codes=["iberia_provider_unavailable_total", "provider_total_outage"],
                message=f"Iberia public provider unavailable for {search.origin}->{search.destination} on {search.travel_date}",
                provider_id=self.provider_id,
                severity="error",
            ) from exc

        flights = extract_public_availability_flights(payload, search)
        warnings_structured: list[ProviderWarning] = []
        if not flights:
            warnings_structured.append(
                ProviderWarning(code="provider_empty_result", provider=self.provider_id, severity="info")
            )
        return ProviderFetchResult(flights=flights, warnings=[], warnings_structured=warnings_structured)

    def _fetch_public_availability(
        self, search: IberiaPublicAvailabilitySearch, *, timeout_ms: int
    ) -> Mapping[str, Any]:
        time.sleep(random.uniform(0.1, 0.4))
        # NOTE: keep headers minimal. curl_cffi's impersonation pairs a realistic
        # Chrome UA, sec-ch-* and sec-fetch-* with the matching TLS fingerprint.
        # Overriding those headers with bare values breaks the pairing and lets
        # Akamai flag the request as a bot (same anti-bot pattern that blocked
        # easyJet before its warmup + UA fix).
        response = self._session.post(
            self._availability_url(),
            json=build_public_availability_request(search),
            timeout=max(2.0, timeout_ms / 1000),
            headers={
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Accept-Language": f"{self.language}-{self.market},{self.language};q=0.9,en;q=0.8",
                "Origin": self.base_url,
                "Referer": f"{self.base_url}/flights/",
                "Authorization": self.authorization,
                "language": self.language,
                "market": self.market,
                "sec-ch-ua": _CHROME131_UA_SIG,
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "sec-fetch-dest": "empty",
                "priority": "u=1, i",
            },
        )
        captcha_kind = self._looks_like_captcha(response)
        if captcha_kind:
            raise ProviderSourceFetchError(
                warning_codes=[
                    f"iberia_provider_captcha_{captcha_kind}",
                    "iberia_provider_unavailable_total",
                    "provider_total_outage",
                ],
                message=f"Iberia WAF returned a bot challenge ({captcha_kind}) for {search.origin}->{search.destination} on {search.travel_date}",
                provider_id=self.provider_id,
                severity="error",
                meta={"reason": captcha_kind},
            )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderSourceFetchError(
                warning_codes=["iberia_provider_unavailable_total", "provider_total_outage"],
                message="Iberia public provider returned a non-JSON response",
                provider_id=self.provider_id,
                severity="error",
                meta={"reason": "invalid_json"},
            ) from exc
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _looks_like_captcha(response: Any) -> str | None:
        """Best-effort detection of Akamai/Datadome bot challenges.

        A real browser impersonation should generally avoid these, but when the
        warmup cookies are stale or the IP gets scored higher, the server may
        serve a challenge page or HTML instead of the JSON payload. We label
        these distinctly so the orchestrator's logs can tell captcha from a
        genuine transport failure.
        """
        status = getattr(response, "status_code", None)
        try:
            text = response.text or ""
        except Exception:
            text = ""
        lowered = text.lower()
        if status == 403:
            if "captcha" in lowered or "_abck" in lowered:
                return "akamai_captcha"
            if "datadome" in lowered or "blocked" in lowered and "captcha-delivery.com" in lowered:
                return "datadome_captcha"
            if "access denied" in lowered or "request rejected" in lowered:
                return "akamai_blocked"
        if "<html" in lowered and ("captcha" in lowered or "challenge" in lowered):
            return "html_captcha"
        return None

    def _warm_session(self, base_url: str, *, referer_path: str = "") -> None:
        """Best-effort warmup to acquire WAF cookies (Akamai _abck / bm_sz).

        Without this, Iberia's NDC endpoint returns bot challenges because the
        request misses the sensor tokens that a real browser would have earned
        during the first navigation to iberia.com. Errors are swallowed: a
        failed warmup is a soft failure, and the actual availability call still
        surfaces the real outcome.
        """
        if self._warmed:
            return
        session_get = getattr(self._session, "get", None)
        if session_get is None:
            # Test doubles / non-curl-cffi fallback: skip without throwing.
            self._warmed = True
            return
        try:
            time.sleep(random.uniform(0.05, 0.2))
            session_get(
                f"{base_url}{referer_path}",
                timeout=2.0,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": f"{self.language}-{self.market},{self.language};q=0.9,en;q=0.8",
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
        self._warmed = True

    def _availability_url(self) -> str:
        path = self.availability_path if self.availability_path.startswith("/") else f"/{self.availability_path}"
        return f"{self.api_base_url}{path}"

    def _build_search(
        self, origin: str, destination: str, travel_date: str, currency: str
    ) -> IberiaPublicAvailabilitySearch:
        return IberiaPublicAvailabilitySearch(
            origin=origin.upper().strip(),
            destination=destination.upper().strip(),
            travel_date=travel_date,
            currency=currency.upper().strip(),
            market=self.market,
            language=self.language,
            base_url=self.base_url,
        )
