"""Makcorps hotel provider adapter.

Enabled when HOTEL_PROVIDER=makcorps and MAKCORPS_API_KEY is set.
No automatic fallback to mock is applied when the API key is missing.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.hotels.contracts import HotelProviderAdapter, ProviderHotelRecord, ProviderRateRecord

logger = logging.getLogger("app.hotels.makcorps")

_MAKCORPS_API_KEY = os.getenv("MAKCORPS_API_KEY", "").strip()
_MAKCORPS_BASE_URL = os.getenv("MAKCORPS_BASE_URL", "https://api.makcorps.com").rstrip("/")
_PROVIDER_TIMEOUT = int(os.getenv("HOTEL_PROVIDER_TIMEOUT_SECONDS", "10"))
_PROVIDER_MAX_RETRIES = int(os.getenv("HOTEL_PROVIDER_MAX_RETRIES", "2"))


def _log_payload(event: str, **fields: Any) -> str:
    return json.dumps({"event": event, **fields}, ensure_ascii=False)


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
            "Authorization": f"Bearer {_MAKCORPS_API_KEY}",
            "Accept": "application/json",
            "User-Agent": "ViruTracker/1.0",
        }
    )
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
    try:
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

    def is_enabled(self) -> bool:
        if not _MAKCORPS_API_KEY:
            logger.warning(_log_payload("makcorps_disabled", reason="MAKCORPS_API_KEY not set"))
            return False
        return True

    def fetch_hotel_rates(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int = 2,
        currency: str = "EUR",
    ) -> list[ProviderRateRecord]:
        """Fetch rates for a specific hotel with search parameters."""
        if not self.is_enabled():
            return []

        url = f"{_MAKCORPS_BASE_URL}/v1/hotels/{hotel_id}/pricing"
        params: dict[str, str | int] = {
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": guests,
            "currency": currency,
        }
        try:
            response = self._session.get(url, params=params, timeout=_PROVIDER_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.warning(
                _log_payload(
                    "makcorps_fetch_hotel_rates_failed",
                    hotel_id=hotel_id,
                    error=str(exc),
                )
            )
            return []

        return self._parse_rates(payload, check_in, check_out)

    def _parse_rates(
        self,
        payload: dict[str, Any] | list[Any],
        expected_check_in: date | None = None,
        expected_check_out: date | None = None,
    ) -> list[ProviderRateRecord]:
        rates: list[ProviderRateRecord] = []

        items = payload if isinstance(payload, list) else payload.get("rates") or payload.get("data") or []
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            return rates

        for rate_item in items:
            if not isinstance(rate_item, dict):
                continue
            check_in = _parse_date(rate_item.get("check_in")) or expected_check_in
            check_out = _parse_date(rate_item.get("check_out")) or expected_check_out
            if check_in is None or check_out is None:
                continue
            if check_out <= check_in:
                continue
            amount = _parse_positive_amount(rate_item.get("amount") or rate_item.get("price"))
            if amount is None:
                continue
            currency = _normalize_currency(rate_item.get("currency"))
            if not currency:
                continue
            rates.append(
                ProviderRateRecord(
                    check_in=check_in,
                    check_out=check_out,
                    amount=amount,
                    currency=currency,
                    guests=int(rate_item.get("guests") or 2),
                    room_label=rate_item.get("room_label") or rate_item.get("room_type"),
                    meal_plan=rate_item.get("meal_plan") or rate_item.get("board"),
                    cancellation_policy=rate_item.get("cancellation_policy"),
                )
            )
        return rates

    def fetch_hotels(self) -> list[ProviderHotelRecord]:
        if not self.is_enabled():
            raise ValueError(
                "Makcorps provider is not enabled. Set MAKCORPS_API_KEY to activate."
            )

        url = f"{_MAKCORPS_BASE_URL}/v1/hotels/pricing"
        try:
            response = self._session.get(url, timeout=_PROVIDER_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
        except ValueError as exc:
            logger.error(_log_payload("makcorps_payload_invalid", url=url))
            raise ValueError("Makcorps response payload is invalid.") from exc
        except requests.exceptions.Timeout as exc:
            logger.error(_log_payload("makcorps_timeout", url=url, timeout=_PROVIDER_TIMEOUT))
            raise ValueError(f"Makcorps request timed out after {_PROVIDER_TIMEOUT}s") from exc
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            logger.error(_log_payload("makcorps_request_failed", url=url, status_code=status_code))
            raise ValueError(f"Makcorps request failed with status {status_code}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error(_log_payload("makcorps_request_failed", url=url, error=str(exc)))
            raise ValueError(f"Makcorps request failed: {exc}") from exc

        return self._parse_response(payload)

    def _parse_response(self, payload: dict[str, Any] | Any) -> list[ProviderHotelRecord]:
        if not isinstance(payload, dict):
            raise ValueError("Makcorps response payload is invalid.")

        records: list[ProviderHotelRecord] = []
        items = payload.get("data") or payload.get("hotels") or []

        if isinstance(items, dict):
            items = [items]
        elif not isinstance(items, list):
            raise ValueError("Makcorps response payload is invalid.")

        for item in items:
            if not isinstance(item, dict):
                continue

            rates: list[ProviderRateRecord] = []
            for rate_item in item.get("rates") or []:
                if not isinstance(rate_item, dict):
                    continue
                check_in = _parse_date(rate_item.get("check_in"))
                check_out = _parse_date(rate_item.get("check_out"))
                if check_in is None or check_out is None:
                    continue
                if check_out <= check_in:
                    continue
                amount = _parse_positive_amount(rate_item.get("amount") or rate_item.get("price"))
                if amount is None:
                    continue
                currency = _normalize_currency(rate_item.get("currency"))
                if not currency:
                    continue

                rates.append(
                    ProviderRateRecord(
                        check_in=check_in,
                        check_out=check_out,
                        amount=amount,
                        currency=currency,
                        guests=int(rate_item.get("guests") or 2),
                        room_label=rate_item.get("room_label") or rate_item.get("room_type"),
                        meal_plan=rate_item.get("meal_plan") or rate_item.get("board"),
                        cancellation_policy=rate_item.get("cancellation_policy"),
                    )
                )

            hotel_id = str(item.get("id") or item.get("hotel_id") or "")
            if not hotel_id:
                continue

            records.append(
                ProviderHotelRecord(
                    provider_hotel_id=hotel_id,
                    raw_name=str(item.get("name") or item.get("hotel_name") or ""),
                    raw_address=item.get("address"),
                    city=str(item.get("city") or ""),
                    country_code=str(item.get("country_code") or item.get("country") or "").upper()[:2],
                    latitude=_parse_optional_float(item.get("latitude")),
                    longitude=_parse_optional_float(item.get("longitude")),
                    stars=_parse_optional_int(item.get("stars")),
                    rates=rates,
                    raw_payload=item,
                )
            )

        return records
