"""Makcorps hotel provider adapter.

Enabled when HOTEL_PROVIDER=makcorps and MAKCORPS_API_KEY is set.
No automatic fallback to mock is applied when the API key is missing.

API docs: https://docs.makcorps.com/
- /mapping?api_key=KEY&name=CityName  → type GEO/HOTEL → document_id
- /city?cityid=ID&checkin=...&checkout=...&adults=N&rooms=1&cur=EUR&pagination=0&api_key=KEY
- /hotel?hotelid=ID&checkin=...&checkout=...&adults=N&rooms=1&cur=EUR&api_key=KEY
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from datetime import date, timedelta
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.request_context import get_client_event_id, get_correlation_id
from app.hotels.contracts import HotelProviderAdapter, ProviderHotelRecord, ProviderRateRecord

logger = logging.getLogger("app.hotels.makcorps")

_MAKCORPS_API_KEY = os.getenv("MAKCORPS_API_KEY", "").strip()
_MAKCORPS_BASE_URL = os.getenv("MAKCORPS_BASE_URL", "https://api.makcorps.com").rstrip("/")
_PROVIDER_TIMEOUT = int(os.getenv("HOTEL_PROVIDER_TIMEOUT_SECONDS", "10"))
_PROVIDER_MAX_RETRIES = int(os.getenv("HOTEL_PROVIDER_MAX_RETRIES", "2"))

_SENSITIVE_KEY_PATTERN = re.compile(
    r'''(?i)(["']?(?:api[_-]?key|token|secret|password|authorization|cookie)["']?\s*[:=]\s*["']?)([^&\s,}"']+)'''
)
_SENSITIVE_PAYLOAD_KEYS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
)


def _redact_sensitive_text(value: object) -> str:
    """Remove query/header-style secrets from exception and payload text."""
    return _SENSITIVE_KEY_PATTERN.sub(r"\1***", str(value)[:2000])


def _redact_provider_payload(value: Any) -> Any:
    """Keep provider diagnostics useful without persisting credentials."""
    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, item in value.items():
            key_text = str(key).lower().replace("-", "_")
            if any(part in key_text for part in _SENSITIVE_PAYLOAD_KEYS):
                redacted[key] = "***"
            else:
                redacted[key] = _redact_provider_payload(item)
        return redacted
    if isinstance(value, list):
        return [_redact_provider_payload(item) for item in value]
    if isinstance(value, str):
        return _redact_sensitive_text(value)
    return value


def _log_payload(event: str, **fields: Any) -> str:
    context = {
        "correlation_id": get_correlation_id() or None,
        "client_event_id": get_client_event_id(),
    }
    return json.dumps(
        {
            "event": event,
            **context,
            **{key: _redact_provider_payload(value) for key, value in fields.items()},
        },
        ensure_ascii=False,
    )


def _build_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=_PROVIDER_MAX_RETRIES,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": "ViruAir/1.0",
        }
    )
    correlation_id = get_correlation_id()
    client_event_id = get_client_event_id()
    if correlation_id:
        session.headers["x-correlation-id"] = correlation_id
    if client_event_id:
        session.headers["x-client-event-id"] = client_event_id
    return session


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _normalize_currency(value: str | None) -> str:
    if not value:
        return ""
    cleaned = str(value).strip().upper()
    if len(cleaned) == 3 and cleaned.isalpha():
        return cleaned
    return ""


def _parse_positive_amount(value: Any) -> float | None:
    """Parse a numeric value, stripping currency symbols and whitespace."""
    try:
        if isinstance(value, str):
            # Strip common currency symbols and whitespace
            cleaned = value.strip()
            # Remove leading currency signs: €, $, £, ¥, etc.
            cleaned = re.sub(r"^[^\d.-]+", "", cleaned)
            cleaned = cleaned.replace(",", "")  # Remove thousand separators
            amount = float(cleaned)
        else:
            amount = float(value)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    return amount


def _parse_optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _parse_optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


class MakcorpsHotelProviderAdapter(HotelProviderAdapter):
    provider_id = "makcorps"

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or _build_session()
        # A provider adapter can be used by area-search worker threads. The
        # requests Session is shared for connection pooling, but requests does
        # not guarantee Session mutation/read safety across threads.
        self._session_lock = threading.RLock()

    # ── helpers ──────────────────────────────────────────────────────

    def is_enabled(self) -> bool:
        if not _MAKCORPS_API_KEY:
            logger.warning(_log_payload("makcorps_disabled", reason="MAKCORPS_API_KEY not set"))
            return False
        return True

    def _auth_params(self) -> dict[str, str]:
        return {"api_key": _MAKCORPS_API_KEY}

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        """Perform a GET request to the Makcorps API, returning parsed JSON or None."""
        merged = {**params, **self._auth_params()}
        url = f"{_MAKCORPS_BASE_URL}{path}"
        try:
            # Keep the shared Session safe while preserving the copied
            # ContextVar (correlation/client intent) in the calling thread.
            with self._session_lock:
                response = self._session.get(url, params=merged, timeout=_PROVIDER_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.warning(
                _log_payload("makcorps_request_failed", path=path, error=_redact_sensitive_text(exc))
            )
            return None

    # ── mapping ──────────────────────────────────────────────────────

    def resolve_city_id(self, city_name: str) -> str | None:
        """Resolve a city name to a Makcorps city ID via the /mapping endpoint."""
        payload = self._get("/mapping", {"name": city_name})
        if not isinstance(payload, list):
            return None

        # Prefer GEO type results; fall back to any result
        for item in payload:
            if isinstance(item, dict) and item.get("type") == "GEO":
                doc_id = item.get("document_id")
                if doc_id:
                    return str(doc_id)
        # Fallback: accept any result
        for item in payload:
            if isinstance(item, dict):
                doc_id = item.get("document_id")
                if doc_id:
                    return str(doc_id)
        return None

    def resolve_hotel_makcorps_id(self, hotel_name: str, city: str = "") -> str | None:
        """Resolve a hotel name to a Makcorps hotel ID via the /mapping endpoint."""
        query = f"{hotel_name}, {city}" if city else hotel_name
        payload = self._get("/mapping", {"name": query})
        if not isinstance(payload, list):
            return None

        for item in payload:
            if isinstance(item, dict) and item.get("type") == "HOTEL":
                doc_id = item.get("document_id")
                if doc_id:
                    return str(doc_id)
        return None

    # ── fetch_hotel_rates (real-time pricing for area_search) ──────

    def fetch_hotel_rates(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int = 2,
        currency: str = "EUR",
    ) -> list[ProviderRateRecord]:
        """Fetch live rates for a specific hotel via the /hotel endpoint.

        `hotel_id` should be the Makcorps internal hotel ID (provider_hotel_id),
        obtained from the /mapping API or from a previous /city response.
        """
        if not self.is_enabled():
            return []

        payload = self._get(
            "/hotel",
            {
                "hotelid": hotel_id,
                "checkin": check_in.isoformat(),
                "checkout": check_out.isoformat(),
                "adults": guests,
                "rooms": 1,
                "cur": currency,
            },
        )
        if payload is None:
            return []

        return self._parse_hotel_rates(payload, check_in, check_out, guests, currency)

    def _parse_hotel_rates(
        self,
        payload: dict[str, Any],
        check_in: date,
        check_out: date,
        guests: int,
        currency: str,
    ) -> list[ProviderRateRecord]:
        """Parse the /hotel endpoint response into ProviderRateRecord list.

        The /hotel endpoint returns:
        {"comparison": [[{vendor1: "Expedia", price1: 376, Totalprice1: 376, tax1: 37.6, ...}, ...]]}

        Each vendor object uses numbered keys (vendor1/price1/tax1, vendor2/price2/tax2, etc.).
        """
        rates: list[ProviderRateRecord] = []

        # comparison is array of arrays: [[{...}, {...}]]
        comparison: list[Any] = []
        if isinstance(payload, list):
            comparison = payload
        elif isinstance(payload, dict):
            comparison = payload.get("comparison") or []
        if not isinstance(comparison, list):
            return rates

        # Extract the inner array (comparison[0])
        vendors: list[Any] = []
        for item in comparison:
            if isinstance(item, list):
                vendors = item
                break
        if not vendors:
            # If comparison was already a flat list of dicts
            vendors = [v for v in comparison if isinstance(v, dict)]
        if not vendors:
            return rates

        for vendor_obj in vendors:
            if not isinstance(vendor_obj, dict):
                continue

            # Find numbered price/tax keys (price1, price2, ...; tax1, tax2, ...)
            price = None
            tax = 0.0
            for key, val in vendor_obj.items():
                if re.match(r"^(Total)?price\d+$", key) and val is not None:
                    p = _parse_positive_amount(val)
                    if p is not None:
                        price = p
                        break
            if price is None:
                # Skip vendors with no valid price (e.g. "sold_out")
                continue

            for key, val in vendor_obj.items():
                if re.match(r"^tax\d+$", key):
                    t = _parse_positive_amount(val)
                    if t is not None:
                        tax = t
                        break

            total = price + tax
            rates.append(
                ProviderRateRecord(
                    check_in=check_in,
                    check_out=check_out,
                    amount=total,
                    currency=currency,
                    guests=guests,
                )
            )

        return rates

    # ── fetch_hotels (bulk ingestion for sweeps) ────────────────────

    def fetch_hotels(
        self,
        city_name: str | None = None,
        city_id: str | None = None,
        check_in: date | None = None,
        check_out: date | None = None,
        guests: int = 2,
        currency: str = "EUR",
        page: int = 0,
    ) -> list[ProviderHotelRecord]:
        """Fetch hotels from a city via the /city endpoint.

        Requires either `city_name` (resolved via /mapping) or a known `city_id`.
        If neither is provided, falls back to HOTEL_SWEEP_CITY env var.
        Dates default to 7-14 days from now if not provided.
        """
        if not self.is_enabled():
            raise ValueError(
                "Makcorps provider is not enabled. Set MAKCORPS_API_KEY to activate."
            )

        # Resolve city_id from name or env fallback
        resolved_name = city_name or os.getenv("HOTEL_SWEEP_CITY", "").strip()
        resolved_id = city_id
        if not resolved_id and resolved_name:
            resolved_id = self.resolve_city_id(resolved_name)
        if not resolved_id:
            raise ValueError(
                "city_id, city_name, or HOTEL_SWEEP_CITY is required for Makcorps fetch_hotels. "
                "Use resolve_city_id(city_name) first, or set HOTEL_SWEEP_CITY in your .env."
            )

        # Default dates: next week, 7-night stay

        today = date.today()
        cin = check_in or (today + timedelta(days=7))
        cout = check_out or (today + timedelta(days=14))

        payload = self._get(
            "/city",
            {
                "cityid": resolved_id,
                "checkin": cin.isoformat(),
                "checkout": cout.isoformat(),
                "adults": guests,
                "rooms": 1,
                "cur": currency,
                "pagination": str(page),
            },
        )
        if payload is None:
            raise ValueError("Makcorps /city request failed or returned no data.")

        return self._parse_city_response(payload, cin, cout, guests, currency)

    def _parse_city_response(
        self,
        payload: dict[str, Any],
        check_in: date,
        check_out: date,
        guests: int,
        currency: str,
    ) -> list[ProviderHotelRecord]:
        """Parse the /city endpoint response into ProviderHotelRecord list.

        The /city endpoint returns:
        {
          "hotels": [...],
          "totalHotelCount": N,
          "totalpageCount": N,
          "currentPageHotelsCount": N,
          "currentPageNumber": N
        }

        Each hotel has: hotelId, name, telephone, geocode, rating, count,
        and optionally comparison data with vendors/prices.
        """
        records: list[ProviderHotelRecord] = []

        if not isinstance(payload, dict):
            return records
        items = payload.get("hotels") or payload.get("data") or []
        if isinstance(items, dict):
            items = [items]
        elif not isinstance(items, list):
            return records

        for item in items:
            if not isinstance(item, dict):
                continue

            hotel_id = str(item.get("hotelId") or item.get("hotel_id") or "")
            if not hotel_id:
                continue

            # Parse pricing from the comparison/vendors array
            rates: list[ProviderRateRecord] = []
            comparison = item.get("comparison") or []
            if isinstance(comparison, dict):
                comparison = [comparison]
            for comp in comparison if isinstance(comparison, list) else []:
                if not isinstance(comp, dict):
                    continue
                price = _parse_positive_amount(comp.get("price"))
                if price is None:
                    continue
                tax = _parse_positive_amount(comp.get("tax")) or 0.0
                total = price + tax
                rates.append(
                    ProviderRateRecord(
                        check_in=check_in,
                        check_out=check_out,
                        amount=total,
                        currency=currency,
                        guests=guests,
                        room_label=comp.get("room_type"),
                        meal_plan=comp.get("meal"),
                        cancellation_policy=comp.get("cancellation"),
                    )
                )

            # Parse geocode
            geocode = item.get("geocode") or {}
            if isinstance(geocode, str):
                try:
                    geocode = json.loads(geocode)
                except (json.JSONDecodeError, TypeError):
                    geocode = {}

            lat = _parse_optional_float(geocode.get("lat") or geocode.get("latitude")) if isinstance(geocode, dict) else None
            lng = _parse_optional_float(geocode.get("lng") or geocode.get("longitude") or geocode.get("lon")) if isinstance(geocode, dict) else None

            name = str(item.get("name") or "")
            city_from_api = str(item.get("city") or "")
            country = str(item.get("country") or "").upper()[:2]

            records.append(
                ProviderHotelRecord(
                    provider_hotel_id=hotel_id,
                    raw_name=name,
                    raw_address=item.get("address"),
                    city=city_from_api,
                    country_code=country,
                    latitude=lat,
                    longitude=lng,
                    stars=_parse_optional_int(item.get("stars") or item.get("rating")),
                    rates=rates,
                    raw_payload=_redact_provider_payload(item),
                )
            )

        return records
