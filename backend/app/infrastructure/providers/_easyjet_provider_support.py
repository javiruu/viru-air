from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final, NoReturn

from app.domain.entities import ProviderSourceFetchError
from app.infrastructure.providers._captcha import WafRule
from app.infrastructure.providers._browser_warmup import request_via_browser_when_enabled
from app.infrastructure.providers.easyjet_flight_connections import EasyJetFlightConnectionsSearch
from app.infrastructure.providers.easyjet_public_availability import EasyJetPublicAvailabilitySearch

CHROME131_UA_SIG: Final = '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"'

EASYJET_WAF_RULES: Final[dict[str, WafRule]] = {
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


@dataclass(frozen=True, slots=True)
class EasyJetSearch:
    origin: str
    destination: str
    travel_date: str
    currency: str


def normalize_search(origin: str, destination: str, travel_date: str, currency: str) -> EasyJetSearch:
    return EasyJetSearch(
        origin=origin.upper().strip(),
        destination=destination.upper().strip(),
        travel_date=travel_date,
        currency=currency.upper().strip(),
    )


def to_public_availability_search(
    search: EasyJetSearch,
    *,
    language_code: str,
    base_url: str,
) -> EasyJetPublicAvailabilitySearch:
    return EasyJetPublicAvailabilitySearch(
        origin=search.origin,
        destination=search.destination,
        travel_date=search.travel_date,
        currency=search.currency,
        language=language_code,
        base_url=base_url,
    )


def to_flight_connections_search(
    search: EasyJetSearch,
    *,
    language_code: str,
    residency: str,
    base_url: str,
) -> EasyJetFlightConnectionsSearch:
    return EasyJetFlightConnectionsSearch(
        origin=search.origin,
        destination=search.destination,
        travel_date=search.travel_date,
        currency=search.currency,
        language=language_code,
        residency=residency,
        base_url=base_url,
    )


def public_availability_headers(base_url: str, language_code: str, residency: str) -> dict[str, str]:
    language = language_code.lower()
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": f"{language}-{residency},{language};q=0.9,en;q=0.8",
        "Origin": base_url,
        "Referer": f"{base_url}/{language}/",
        "sec-ch-ua": CHROME131_UA_SIG,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-fetch-dest": "empty",
    }


def flight_connections_headers(
    flight_connections_url: str,
    language_code: str,
    residency: str,
    bypass_secret: str,
) -> dict[str, str]:
    language = language_code.lower()
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": f"{language}-{residency},{language};q=0.9,en;q=0.8",
        "Origin": flight_connections_url,
        "Referer": f"{flight_connections_url}/{language}/",
        "sec-ch-ua": CHROME131_UA_SIG,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-fetch-dest": "empty",
        "content-type": "application/json",
    }
    if bypass_secret:
        headers["X-Dohop-Bypass"] = bypass_secret
    return headers


def warmup_headers(language_code: str, residency: str) -> dict[str, str]:
    language = language_code.lower()
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": f"{language}-{residency},{language};q=0.9,en;q=0.8",
        "sec-ch-ua": CHROME131_UA_SIG,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-dest": "document",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
    }


def request_with_optional_browser(
    session: Any,
    method: str,
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    json_body: Mapping[str, Any] | None = None,
    headers: Mapping[str, str],
    timeout_ms: int,
    warmup_url: str | None = None,
    warmup_referer_path: str = "",
) -> Any:
    browser_response = request_via_browser_when_enabled(
        "EASYJET_USE_BROWSER_POST",
        method,
        url,
        json_body=json_body,
        headers=headers,
        timeout_ms=timeout_ms,
        warmup_url=warmup_url,
        warmup_referer_path=warmup_referer_path,
    )
    if browser_response is not None:
        return browser_response
    if method == "POST":
        session_post = getattr(session, "post", None)
        if callable(session_post):
            return session_post(
                url,
                json=dict(json_body) if json_body else None,
                headers=dict(headers),
                timeout=max(2.0, timeout_ms / 1000),
            )
    return session.get(
        url,
        params=dict(params or json_body or {}),
        headers=dict(headers),
        timeout=max(2.0, timeout_ms / 1000),
    )


def raise_waf_challenge(
    *,
    search: EasyJetSearch,
    captcha_kind: str,
    warning_prefix: str,
    message_subject: str,
) -> NoReturn:
    raise ProviderSourceFetchError(
        warning_codes=[
            f"{warning_prefix}_{captcha_kind}",
            "easyjet_provider_unavailable_total",
            "provider_total_outage",
        ],
        message=f"{message_subject} WAF returned a bot challenge ({captcha_kind}) for {search.origin}->{search.destination} on {search.travel_date}",
        provider_id="easyjet",
        severity="error",
        meta={"reason": captcha_kind},
    )


def raise_invalid_json(source_error: Exception) -> NoReturn:
    raise ProviderSourceFetchError(
        warning_codes=["easyjet_provider_unavailable_total", "provider_total_outage"],
        message="easyJet provider returned a non-JSON response",
        provider_id="easyjet",
        severity="error",
        meta={"reason": "invalid_json"},
    ) from source_error


def raise_provider_unavailable(search: EasyJetSearch, source_error: Exception) -> NoReturn:
    raise ProviderSourceFetchError(
        warning_codes=["easyjet_provider_unavailable_total", "provider_total_outage"],
        message=f"easyJet provider unavailable for {search.origin}->{search.destination} on {search.travel_date}",
        provider_id="easyjet",
        severity="error",
    ) from source_error
