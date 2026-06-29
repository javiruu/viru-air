from __future__ import annotations

import logging
import os
import random
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Any
try:
    from curl_cffi import requests
    from curl_cffi.requests.errors import RequestsError
except ImportError:
    import requests
    from requests.exceptions import RequestException as RequestsError
import ssl
from requests.adapters import HTTPAdapter

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFetchResult, ProviderFlight, ProviderSourceFetchError, ProviderWarning
from app.infrastructure.providers.base import FlightProvider

logger = logging.getLogger(__name__)

_PROVIDER_POOL_SIZE = 32

class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = ctx
        super().init_poolmanager(*args, **kwargs)

class WizzAirProvider(FlightProvider):
    provider_id = "wizzair"

    def __init__(
        self,
        *,
        base_url: str = "https://be.wizzair.com/29.4.0/Api",
        day_interval: int | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("WIZZAIR_BASE_URL", "https://be.wizzair.com/29.4.0/Api")).rstrip("/")
        self.day_interval = max(3, int(day_interval or os.getenv("WIZZAIR_FARECHART_DAY_INTERVAL", "9")))
        try:
            self._session = requests.Session(impersonate="chrome110")
        except TypeError:
            self._session = requests.Session()
            adapter = TLSAdapter(pool_connections=_PROVIDER_POOL_SIZE, pool_maxsize=_PROVIDER_POOL_SIZE)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
        self._cache_lock = threading.Lock()
        self._cache: dict[tuple[str, str, str], list[ProviderFlight]] = {}
        # Per-route locks: prevent duplicate Wizz Air requests only for the SAME route.
        # Different routes (e.g. MAD->BCN vs MAD->DUB) can fetch in parallel.
        # This avoids the 400 Bad Request (InvalidProtocol) from Wizz Air's API
        # when multiple requests hit the same route simultaneously, while still
        # allowing full concurrency across different routes.
        self._route_locks: dict[tuple[str, str], threading.Lock] = {}
        self._route_locks_lock = threading.Lock()

    def is_enabled(self) -> bool:
        return True

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        origin = origin.upper().strip()
        destination = destination.upper().strip()

        cache_key = (origin, destination, travel_date)
        route_key = (origin, destination)

        # ── Cache check: fast path, no route lock needed ──
        with self._cache_lock:
            if cache_key in self._cache:
                flights = self._cache[cache_key]
                logger.debug(
                    "wizzair_cache_hit route=%s->%s date=%s flights=%s",
                    origin, destination, travel_date, len(flights),
                )
                return ProviderFetchResult(flights=flights, warnings=[], warnings_structured=[])

        # ── Per-route lock: only serialize same-origin/destination fetches ──
        with self._route_locks_lock:
            route_lock = self._route_locks.get(route_key)
            if route_lock is None:
                route_lock = threading.Lock()
                self._route_locks[route_key] = route_lock

        with route_lock:
            # Double-check cache inside the lock (another thread may have populated it)
            with self._cache_lock:
                if cache_key in self._cache:
                    flights = self._cache[cache_key]
                    return ProviderFetchResult(flights=flights, warnings=[], warnings_structured=[])

            # ── Fetch from Wizz Air API ──
            logger.info(
                "wizzair_fetch_start route=%s->%s date=%s timeout_ms=%s",
                origin, destination, travel_date, timeout_ms,
            )
            t0 = time.perf_counter()
            try:
                body = self._fetch_farechart(origin, destination, travel_date, timeout_ms=timeout_ms)
            except RequestsError as exc:
                elapsed = int((time.perf_counter() - t0) * 1000)
                logger.warning(
                    "wizzair_fetch_failed route=%s->%s date=%s elapsed_ms=%s error=%s",
                    origin, destination, travel_date, elapsed, str(exc)[:120],
                )
                raise ProviderSourceFetchError(
                    warning_codes=["wizzair_provider_unavailable_total", "provider_total_outage"],
                    message=f"Wizz Air provider unavailable for {origin}->{destination} on {travel_date}",
                    provider_id=self.provider_id,
                    severity="error",
                ) from exc

            elapsed = int((time.perf_counter() - t0) * 1000)
            logger.info(
                "wizzair_fetch_done route=%s->%s date=%s elapsed_ms=%s",
                origin, destination, travel_date, elapsed,
            )

            # Parse and cache all flights from the response
            all_parsed_flights = self._extract_all_flights(body, origin=origin, destination=destination, fallback_currency=currency)
            
            with self._cache_lock:
                for parsed_date, flight_list in all_parsed_flights.items():
                    self._cache[(origin, destination, parsed_date)] = flight_list
                if cache_key not in self._cache:
                    self._cache[cache_key] = []
                flights = self._cache[cache_key]

        warnings_structured: list[ProviderWarning] = []
        if not flights:
            warnings_structured.append(
                ProviderWarning(
                    code="provider_empty_result",
                    provider=self.provider_id,
                    severity="info",
                )
            )
        return ProviderFetchResult(flights=flights, warnings=[], warnings_structured=warnings_structured)

    def _fetch_farechart(
        self, origin: str, destination: str, travel_date: str, *, timeout_ms: int
    ) -> dict[str, Any]:
        url = f"{self.base_url}/asset/farechart"
        payload = {
            "isRescueFare": False,
            "adultCount": 1,
            "childCount": 0,
            "dayInterval": self.day_interval,
            "wdc": False,
            "isFlightChange": False,
            "flightList": [
                {
                    "departureStation": origin,
                    "arrivalStation": destination,
                    "date": f"{travel_date}T00:00:00",
                }
            ],
        }
        time.sleep(random.uniform(0.1, 0.4))
        response = self._session.post(
            url,
            json=payload,
            timeout=max(2.0, timeout_ms / 1000),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Origin": "https://www.wizzair.com",
                "Referer": "https://www.wizzair.com/",
            },
        )
        response.raise_for_status()
        return response.json()

    def _extract_all_flights(
        self,
        payload: dict[str, Any],
        *,
        origin: str,
        destination: str,
        fallback_currency: str,
    ) -> dict[str, list[ProviderFlight]]:
        flights_by_date: dict[str, list[ProviderFlight]] = defaultdict(list)
        for item in payload.get("outboundFlights") or []:
            item_date = self._to_iso_date(item.get("date"))
            if not item_date:
                continue

            price = item.get("price") or {}
            amount = price.get("exchangedAmount")
            currency = price.get("exchangedCurrencyCode")
            if amount is None:
                amount = price.get("amount")
            if currency is None:
                currency = price.get("currencyCode") or fallback_currency
            
            if item.get("priceType") == "noData" or amount is None:
                continue

            try:
                normalized_amount = float(amount)
            except (TypeError, ValueError):
                continue
                
            if normalized_amount <= 0.0:
                continue

            flights_by_date[item_date].append(
                ProviderFlight(
                    price=normalized_amount,
                    currency=str(currency).upper(),
                    departure_time_local=None,
                    captured_at=utc_now_naive(),
                    source="wizzair-farechart",
                    deeplink_url=f"https://www.wizzair.com/es-es/booking/select-flight/{origin}/{destination}/{item_date}/null/1/0/0/null"
                )
            )
        return dict(flights_by_date)

    def _to_iso_date(self, value: Any) -> str | None:
        if not value:
            return None
        if isinstance(value, str) and len(value) >= 10:
            raw = value[:10]
            try:
                return datetime.fromisoformat(raw).date().isoformat()
            except ValueError:
                return raw
        return None
