"""Makcorps hotel provider adapter.

Enabled when HOTEL_PROVIDER=makcorps and MAKCORPS_API_KEY is set.
Falls back to mock gracefully when API key is missing.
"""

from __future__ import annotations

import json
import logging
import os
import time
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
        return "EUR"
    cleaned = str(value).strip().upper()
    if len(cleaned) == 3 and cleaned.isalpha():
        return cleaned
    return "EUR"


class MakcorpsHotelProviderAdapter(HotelProviderAdapter):
    provider_id = "makcorps"

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or _build_session()

    def is_enabled(self) -> bool:
        if not _MAKCORPS_API_KEY:
            logger.warning(
                json.dumps(
                    {
                        "event": "makcorps_disabled",
                        "reason": "MAKCORPS_API_KEY not set",
                    },
                    ensure_ascii=False,
                )
            )
            return False
        return True

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
        except requests.exceptions.Timeout as exc:
            logger.error(
                json.dumps(
                    {"event": "makcorps_timeout", "url": url, "timeout": _PROVIDER_TIMEOUT},
                    ensure_ascii=False,
                )
            )
            raise ValueError(f"Makcorps request timed out after {_PROVIDER_TIMEOUT}s") from exc
        except requests.exceptions.RequestException as exc:
            logger.error(
                json.dumps(
                    {"event": "makcorps_request_failed", "url": url, "error": str(exc)},
                    ensure_ascii=False,
                )
            )
            raise ValueError(f"Makcorps request failed: {exc}") from exc

        return self._parse_response(payload)

    def _parse_response(self, payload: dict[str, Any]) -> list[ProviderHotelRecord]:
        records: list[ProviderHotelRecord] = []
        items = payload.get("data") or payload.get("hotels") or []

        if isinstance(items, dict):
            items = [items]

        for item in items:
            rates: list[ProviderRateRecord] = []
            for rate_item in item.get("rates") or []:
                check_in = _parse_date(rate_item.get("check_in"))
                check_out = _parse_date(rate_item.get("check_out"))
                if check_in is None or check_out is None:
                    continue
                if check_out <= check_in:
                    continue

                rates.append(
                    ProviderRateRecord(
                        check_in=check_in,
                        check_out=check_out,
                        amount=float(rate_item.get("amount") or rate_item.get("price") or 0),
                        currency=_normalize_currency(rate_item.get("currency")),
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
                    latitude=float(item["latitude"]) if item.get("latitude") is not None else None,
                    longitude=float(item["longitude"]) if item.get("longitude") is not None else None,
                    stars=int(item["stars"]) if item.get("stars") is not None else None,
                    rates=rates,
                    raw_payload=item,
                )
            )

        return records
