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
from app.infrastructure.providers._browser_warmup import (
    request_via_browser_when_enabled,
    warm_session_with_browser,
)
from app.infrastructure.providers._captcha import WafRule, detect_captcha_kind
from app.infrastructure.providers._session_factory import build_session_kwargs

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


# Each rule: kind -> predicate(status, lowered_text). Order matters: put the
# specific captcha kinds before the generic akamai_blocked deny page so the
# richer signal wins.
#
# Iberia's WAF is Akamai (sensor cookies _abck / bm_sz). The earlier code
# carried a datadome_captcha branch as a defensive remainder, but in practice
# every Iberia challenge body that mentions Datadome also mentions "captcha",
# so the akamai_captcha rule above always wins first. We keep the rule set
# intentionally tight to avoid dead branches.
_IBERIA_WAF_RULES: Final[dict[str, WafRule]] = {
    "akamai_captcha": lambda status, text: status == 403
    and ("captcha" in text or "_abck" in text),
    "akamai_blocked": lambda status, text: status == 403
    and ("access denied" in text or "request rejected" in text),
    "html_captcha": lambda status, text: "<html" in text
    and ("captcha" in text or "challenge" in text),
}


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
            session_kwargs = build_session_kwargs(
                impersonate_env=_IMPERSONATE_ENV_VAR,
                extra_fp_env="IBERIA_EXTRA_FP",
                proxy_env="IBERIA_PROXY",
                ja3_env="IBERIA_JA3",
            )
            # Honour the explicit ``impersonate`` ctor kwarg over the env var.
            session_kwargs["impersonate"] = impersonate_version
            self._session = requests.Session(**session_kwargs)
        except TypeError:
            # stdlib ``requests`` (test doubles / curl_cffi import failure):
            # drop curl_cffi-only kwargs and fall back to a vanilla pool.
            self._session = requests.Session()
            adapter = HTTPAdapter(pool_connections=_PROVIDER_POOL_SIZE, pool_maxsize=_PROVIDER_POOL_SIZE)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
        # Sessions reuse cookies across calls, so the warm-up marker sticks for
        # the lifetime of the provider (matches ThreadPoolExecutor lifespan).
        self._warmed = False
        self._warmed_browser = False

    def is_enabled(self) -> bool:
        return bool(self.base_url and self.api_base_url and self.authorization and self.market and self.language)

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        search = self._build_search(origin, destination, travel_date, currency)
        self._warm_session(self.base_url, referer_path="/")
        try:
            payload = self._fetch_public_availability(search, timeout_ms=timeout_ms)
        except ProviderSourceFetchError:
            # Captcha / source-specific failures: propagate unchanged so the
            # orchestrator sees the rich warning_codes the helper produced.
            raise
        except (RequestsError, ValueError) as exc:
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
        # Build the headers dict once so the curl path and the optional
        # ``request_via_browser`` path share the exact same outbound signal.
        post_headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Accept-Language": f"{self.language}-{self.market},{self.language};q=0.9,en;q=0.8",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
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
        }

        response = self._post_with_optional_browser(
            self._availability_url(),
            json_body=build_public_availability_request(search),
            headers=post_headers,
            timeout_ms=timeout_ms,
        )
        captcha_kind = detect_captcha_kind(response, rules=_IBERIA_WAF_RULES)
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

    def _warm_session(self, base_url: str, *, referer_path: str = "") -> None:
        """Best-effort warmup to acquire WAF cookies (Akamai _abck / bm_sz).

        Without this, Iberia's NDC endpoint returns bot challenges because the
        request misses the sensor tokens that a real browser would have earned
        during the first navigation to iberia.com. Errors are swallowed: a
        failed warmup is a soft failure, and the actual availability call still
        surfaces the real outcome.

        When ``IBERIA_USE_BROWSER_WARMUP=1`` is set, an optional Playwright
        headless navigation is layered on top of the curl warmup so we can
        harvest the JS-set sensor cookies (Akamai's bot manager requires the
        _abck / bm_sz tokens that only real browser JS execution produces).
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
        self._browser_warmup(base_url, referer_path=referer_path)

    def _browser_warmup(self, base_url: str, *, referer_path: str) -> None:
        if self._warmed_browser:
            return
        if warm_session_with_browser(
            self._session,
            env_var="IBERIA_USE_BROWSER_WARMUP",
            base_url=base_url,
            referer_path=referer_path,
        ):
            self._warmed_browser = True

    def _post_with_optional_browser(
        self,
        url: str,
        *,
        json_body: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout_ms: int,
    ) -> Any:
        br = request_via_browser_when_enabled(
            "IBERIA_USE_BROWSER_POST",
            "POST",
            url,
            json_body=dict(json_body),
            headers=dict(headers),
            timeout_ms=timeout_ms,
            warmup_url=self.base_url,
            warmup_referer_path="/",
        )
        if br is not None:
            return br
        return self._session.post(
            url, json=dict(json_body), headers=dict(headers), timeout=max(2.0, timeout_ms / 1000)
        )

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
