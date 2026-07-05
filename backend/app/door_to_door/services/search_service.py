import json
import logging
from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from functools import partial

from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.providers.circuit_breaker import (
    ProviderCircuitBreaker,
    default_circuit_breaker,
)
from app.door_to_door.domain.scoring import score_itinerary
from app.door_to_door.schemas import (
    DoorToDoorCapabilityState,
    DoorToDoorConfidence,
    DoorToDoorFlightOut,
    DoorToDoorLegOut,
    DoorToDoorMapCapabilityOut,
    DoorToDoorMode,
    DoorToDoorOptionOut,
    DoorToDoorPreferences,
    DoorToDoorProviderStatusOut,
    DoorToDoorSearchRequest,
    DoorToDoorSearchResponse,
    DoorToDoorSortBy,
    DoorToDoorSourceOut,
    DoorToDoorSourceType,
    DoorToDoorSummaryOut,
    DoorToDoorWarningOut,
)
from app.door_to_door.services.itinerary_builder import build_summary
from app.infrastructure.db.models import DoorToDoorChosenOption, DoorToDoorSearchHistory

logger = logging.getLogger("app.door_to_door")

GROUND_MODES: set[DoorToDoorMode] = {"bus", "train", "rideshare", "shuttle", "taxi", "car", "walking"}

# Source quality tiers for arbitration (Fase 6).
# Higher = better data. Used to prefer the best source per trip segment
# and to boost scoring for options from higher-quality sources.
SOURCE_QUALITY: dict[DoorToDoorSourceType, int] = {
    "api": 5,
    "open_data": 4,
    "maps": 3,
    "deeplink": 2,
    "external_deeplink": 2,
    "aggregator": 2,
    "scraper": 1,
    "mock": 0,
    "estimate": 0,
}

# Eco-route (Fase 12): per-mode carbon-dioxide estimate, expressed in kg CO2e
# per passenger-kilometer. Values are conservative public averages — meant to
# give users an honest relative-comparison signal, not a certified footprint.
# Walking and any zero-distance supplemental legs contribute zero.
CO2_KG_PER_KM: dict[DoorToDoorMode, float] = {
    "flight": 0.255,
    "car": 0.171,
    "taxi": 0.171,
    "rideshare": 0.080,
    "shuttle": 0.150,
    "bus": 0.103,
    "train": 0.041,
    "walking": 0.0,
}

# Fallback speeds when only duration is known (used to infer km from minutes).
# Conservative averages tuned for short-haul door-to-door legs.
AVG_KMH_INFERENCE: dict[DoorToDoorMode, float] = {
    "flight": 800.0,
    "car": 80.0,
    "taxi": 80.0,
    "rideshare": 80.0,
    "shuttle": 60.0,
    "bus": 50.0,
    "train": 100.0,
    "walking": 5.0,
}


class DoorToDoorSearchService:
    def __init__(
        self,
        providers: list[DoorToDoorProvider] | None = None,
        provider_statuses: list[DoorToDoorProviderStatusOut] | None = None,
        mock_enabled: bool = False,
        circuit_breaker: ProviderCircuitBreaker | None = None,
    ) -> None:
        self.providers = providers or []
        self.provider_statuses = provider_statuses or []
        self.mock_enabled = mock_enabled
        # Share the process-wide singleton so trips survive between requests.
        # Tests can inject a stub via the kwarg.
        self.circuit_breaker = circuit_breaker or default_circuit_breaker()

    async def search(
        self,
        *,
        db: Session,
        user_id: str,
        request: DoorToDoorSearchRequest,
        flight: DoorToDoorFlightOut,
        bootstrap_warnings: list[DoorToDoorWarningOut] | None = None,
    ) -> DoorToDoorSearchResponse:
        checked_at = datetime.now(tz=flight.departure_at.tzinfo)
        query = DoorToDoorProviderQuery(
            origin=request.origin,
            final_destination=request.final_destination,
            preferences=request.preferences,
            flight=flight,
            checked_at=checked_at,
        )

        # Fase 9: structured log — search start
        logger.info(
            json.dumps(
                {
                    "event": "door_to_door_search_start",
                    "user_id": user_id,
                    "watch_id": request.flight_watch_id,
                    "origin": request.origin.label,
                    "destination": request.final_destination.label,
                    "providers": [p.provider_name for p in self.providers],
                },
                ensure_ascii=False,
            )
        )

        warnings: list[DoorToDoorWarningOut] = list(bootstrap_warnings or [])
        options: list[DoorToDoorOptionOut] = []
        has_real_results = False
        has_mock_results = False

        for provider in self.providers:
            try:
                # functools.partial binds `query` once and avoids late-binding of
                # `provider` if this loop ever runs concurrently.
                provider_options = await self.circuit_breaker.run(
                    provider.provider_name,
                    partial(provider.run_search, query),
                )
                if provider_options is None:
                    # Circuit breaker is open: skip this provider without raising.
                    self._append_warning(
                        warnings,
                        DoorToDoorWarningOut(
                            code="PROVIDER_CIRCUIT_OPEN",
                            provider=provider.provider_name,
                            message=(
                                f"Proveedor '{provider.provider_name}' omitido por circuit breaker. "
                                "Se reintentará tras la ventana de recuperación."
                            ),
                        ),
                    )
                    continue
                options.extend(provider_options)
                if provider_options:
                    if provider.source_type in ("mock", "estimate"):
                        has_mock_results = True
                    else:
                        has_real_results = True
                provider_warnings = provider.consume_warnings()
                for warning in provider_warnings:
                    self._append_warning(warnings, warning)

                # Fase 9: structured log — per-provider result
                logger.info(
                    json.dumps(
                        {
                            "event": "door_to_door_provider_result",
                            "user_id": user_id,
                            "provider": provider.provider_name,
                            "source_type": provider.source_type,
                            "options_count": len(provider_options),
                            "warnings": [w.code for w in provider_warnings],
                        },
                        ensure_ascii=False,
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive log path
                logger.warning(
                    json.dumps(
                        {
                            "event": "door_to_door_provider_failed",
                            "provider": provider.provider_name,
                            "user_id": user_id,
                            "error": str(exc),
                        },
                        ensure_ascii=False,
                    )
                )
                self._append_warning(
                    warnings,
                    DoorToDoorWarningOut(
                        code="PROVIDER_PARTIAL_COVERAGE",
                        provider=provider.provider_name,
                        message="Una fuente no ha respondido a tiempo. Te mostramos las opciones con datos suficientes.",
                    ),
                )
                if provider.provider_name == "google_routes":
                    self._append_warning(
                        warnings,
                        DoorToDoorWarningOut(
                            code="GOOGLE_ROUTES_UNAVAILABLE",
                            provider=provider.provider_name,
                            message="No hemos podido calcular rutas terrestres reales con Google en este momento.",
                        ),
                    )

        options = self._enrich_deeplink_with_google_routes(options)

        # Fase 12: eco-route enrichment. Pylons computed locally from
        # distance / duration + mode; per-leg and per-option totals are
        # surfaced honestly with `confidence='estimated'` via the eco_route
        # capability card. Has no side effects on provider ordering once we
        # have completed arbitration, so it runs at the tail of the merge
        # pipeline just before scoring/sorting.
        options = self._enrich_eco_route(options, passengers=request.preferences.passengers)
        # Fase 6: compose cross-provider options (best outbound + best inbound)
        composite = self._compose_cross_provider(options, flight, query)
        if composite:
            options.append(composite)
        options, filter_warnings = self._apply_preferences(options, request.preferences)
        warnings.extend(filter_warnings)

        if options:
            if has_mock_results:
                if not has_real_results:
                    self._append_warning(
                        warnings,
                        DoorToDoorWarningOut(
                            code="NO_REAL_PROVIDER_COVERAGE",
                            message="Sin cobertura real todavía: no hay providers reales activos para esta ruta.",
                        ),
                    )
                self._append_warning(
                    warnings,
                    DoorToDoorWarningOut(
                        code="ESTIMATED_MOCK_DATA",
                        message="Algunas rutas usan estimaciones orientativas mientras se conectan fuentes reales.",
                    ),
                )
        else:
            if not self._has_enabled_real_search_provider():
                self._append_warning(
                    warnings,
                    DoorToDoorWarningOut(
                        code="NO_REAL_PROVIDER_COVERAGE",
                        message="Sin cobertura real todavía: no hay providers reales activos para esta ruta.",
                    ),
                )
            self._append_warning(
                warnings,
                DoorToDoorWarningOut(
                    code="NO_COVERAGE",
                    message="No hay datos suficientes para montar una ruta completa con estos filtros.",
                ),
            )

        options = self._sort_options(options, request.preferences.sort_by)
        summary = build_summary(options)

        # Fase 9: structured log — search end
        completions = [o.completeness for o in options]
        logger.info(
            json.dumps(
                {
                    "event": "door_to_door_search_end",
                    "user_id": user_id,
                    "total_options": len(options),
                    "full": completions.count("full"),
                    "partial_actionable": completions.count("partial_actionable"),
                    "exploratory": completions.count("exploratory"),
                    "warning_codes": [w.code for w in warnings],
                },
                ensure_ascii=False,
            )
        )

        chosen = db.scalar(
            select(DoorToDoorChosenOption)
            .where(
                DoorToDoorChosenOption.user_id == user_id,
                DoorToDoorChosenOption.watch_id == request.flight_watch_id,
            )
            .order_by(DoorToDoorChosenOption.chosen_at.desc(), DoorToDoorChosenOption.id.desc())
        )
        if chosen and any(option.id == chosen.option_id for option in options):
            summary.chosen_option_id = chosen.option_id

        history = self._store_history(db, user_id, request, summary, options, warnings)
        summary.history_id = history.id
        self._prune_old_history(db, user_id)

        return DoorToDoorSearchResponse(flight=flight, summary=summary, options=options, warnings=warnings, map_capabilities=self._build_map_capabilities(checked_at, options, warnings))

    def _has_enabled_real_search_provider(self) -> bool:
        for item in self.provider_statuses:
            if item.enabled and item.source_type not in ("mock", "estimate") and item.supports_search:
                return True
        return False

    def _build_map_capabilities(
        self,
        checked_at: datetime,
        options: list[DoorToDoorOptionOut],
        warnings: list[DoorToDoorWarningOut],
    ) -> dict[str, DoorToDoorMapCapabilityOut]:
        provider_by_name = {item.name: item for item in self.provider_statuses}
        has_google_routes = provider_by_name.get("google_routes", None)
        has_google_routes_enabled = has_google_routes is not None and has_google_routes.enabled
        has_gtfs = provider_by_name.get("gtfs_transit", None)
        has_gtfs_enabled = has_gtfs is not None and has_gtfs.enabled
        has_google_places = provider_by_name.get("google_places", None)
        has_google_places_enabled = has_google_places is not None and has_google_places.enabled

        has_options = len(options) > 0

        MapSourceType = DoorToDoorSourceType | Literal["none"]  # type: ignore[valid-type]

        def _cap(state: DoorToDoorCapabilityState, source_type: MapSourceType, confidence: DoorToDoorConfidence, *, why_missing: str | None = None) -> DoorToDoorMapCapabilityOut:
            return DoorToDoorMapCapabilityOut(
                state=state,
                source_type=source_type,
                confidence=confidence,
                last_checked_at=checked_at,
                why_missing=why_missing,
            )

        return {
            # ── Capacidades con valor real (Fase 9) ──
            "navigation": _cap("available", "maps", "live") if has_google_routes_enabled else _cap("planned", "none", "unavailable", why_missing="google_routes_disabled"),
            "transit": _cap("partial", "open_data", "cached", why_missing="corridor_limited") if has_gtfs_enabled else _cap("planned", "none", "unavailable", why_missing="gtfs_provider_disabled"),
            "alternatives": _cap("available", "api", "cached") if has_options else _cap("planned", "none", "unavailable", why_missing="route_candidates_pending"),
            "saved_places": _cap("available", "api", "cached"),
            # ── Fase 7: capacidades activadas con backend real ──
            "traffic": _cap("partial", "maps", "cached", why_missing="driving_only") if has_google_routes_enabled else _cap("planned", "none", "unavailable", why_missing="google_routes_disabled"),
            "nearby_pois": _cap("partial", "maps", "cached", why_missing="search_endpoint_not_wired") if has_google_places_enabled else _cap("planned", "none", "unavailable", why_missing="google_places_disabled"),
            # ── Capacidades sembradas, sin backend real ──
            "street_view_preview": _cap("planned", "none", "unavailable", why_missing="street_view_not_connected"),
            "offline": _cap("planned", "none", "unavailable", why_missing="offline_cache_not_implemented"),
            "incidents": _cap("planned", "none", "unavailable", why_missing="incident_source_not_connected"),
            "eco_route": _cap("available", "estimate", "estimated") if has_options else _cap("planned", "none", "unavailable", why_missing="route_candidates_pending"),
        }

    def _apply_preferences(
        self,
        options: list[DoorToDoorOptionOut],
        preferences: DoorToDoorPreferences,
    ) -> tuple[list[DoorToDoorOptionOut], list[DoorToDoorWarningOut]]:
        warnings: list[DoorToDoorWarningOut] = []
        filtered = [option for option in options if self._option_matches_modes(option, preferences)]

        if len(filtered) < len(options):
            warnings.append(
                DoorToDoorWarningOut(
                    code="FILTERED_BY_TRANSPORT_PREFERENCES",
                    message="Algunas opciones se han ocultado por tus filtros de transporte.",
                )
            )

        if preferences.max_price is not None:
            before_price = len(filtered)
            filtered = [
                option
                for option in filtered
                if option.total_price_min is None or option.total_price_min <= preferences.max_price
            ]
            if len(filtered) < before_price:
                warnings.append(
                    DoorToDoorWarningOut(
                        code="FILTERED_BY_MAX_PRICE",
                        message="Algunas opciones se han ocultado porque superan el precio máximo del grupo.",
                    )
                )
            if any(option.total_price_min is None for option in filtered):
                warnings.append(
                    DoorToDoorWarningOut(
                        code="UNCONFIRMED_PRICE",
                        message="Hay opciones sin precio confirmado que se mantienen para que puedas abrir el proveedor.",
                    )
                )

        return filtered, warnings

    def _enrich_eco_route(
        self,
        options: list[DoorToDoorOptionOut],
        *,
        passengers: int = 1,
    ) -> list[DoorToDoorOptionOut]:
        """Estimate per-leg and per-option CO2e in kg based on distance or duration.

        Per-leg math (per passenger):
        1. `distance_meters` when known — direct km × factor.
        2. `duration_minutes` × mode-average km/h fallback — used when providers
           only emit schedule data (e.g. GTFS `cached` flights, deeplink-only
           legs without a `distance_meters`).
        3. Skip — too little info to be honest. We refuse to surface a 0 kg
           estimate that would falsely look clean.

        Per-option total scales with `passengers` so a 4-pax trip reports the
        full party footprint, not a single-pax slice. `leg.co2_kg` stays per
        passenger — the legs sum to a per-pax subtotal, multiplied at the
        option boundary — so analytics can show both breakdowns cheaply.

        We surface two complementary boundaries on the option:
          * `co2_per_pax_kg` = leg_sum_per_pax (single-passenger footprint)
          * `total_co2_kg` = co2_per_pax_kg × passengers (full-party footprint)
        Both default to None so callers that never asked for an eco estimate
        see no change in payload shape.

        If at least one leg was estimable, we surface both fields; otherwise
        both stay None so the FE doesn't render a precise-by-zero number
        that means "we know it's zero".
        """
        if not options:
            return options
        # Pydantic `DoorToDoorPreferences.passengers = ge=1, le=9` already
        # clamps the value, so we trust the input here. Defense-in-depth
        # `max(1, int(...))` was redundant and hid clamp changes from the
        # caller — dropped it.
        party = int(passengers)
        enriched: list[DoorToDoorOptionOut] = []
        for option in options:
            leg_total_per_pax_kg = 0.0
            estimated_any = False
            new_legs: list[DoorToDoorLegOut] = []
            for leg in option.legs:
                kg = self._estimate_leg_co2_kg(leg)
                if kg is None:
                    new_legs.append(leg.model_copy())
                    continue
                estimated_any = True
                leg_total_per_pax_kg += kg
                new_legs.append(leg.model_copy(update={"co2_kg": round(kg, 3)}))
            if estimated_any:
                # Round to 2 decimals: orientation figures, not audited, and
                # it dampens cumulative floating-point drift when a 4-pax
                # trip multiplies a multi-leg per-pax subtotal.
                co2_per_pax = round(leg_total_per_pax_kg, 2)
                total = round(co2_per_pax * party, 2)
            else:
                co2_per_pax = None
                total = None
            enriched.append(
                option.model_copy(
                    update={
                        "legs": new_legs,
                        "total_co2_kg": total,
                        "co2_per_pax_kg": co2_per_pax,
                    }
                )
            )
        return enriched

    @staticmethod
    def _estimate_leg_co2_kg(leg: DoorToDoorLegOut) -> float | None:
        """Return kg CO2e for a leg, or None if there's not enough data."""
        if leg.co2_kg is not None:
            return leg.co2_kg
        factor = CO2_KG_PER_KM.get(leg.mode)
        if factor is None:
            return None
        km: float | None = None
        if leg.distance_meters is not None and leg.distance_meters > 0:
            km = leg.distance_meters / 1000.0
        elif leg.duration_minutes is not None and leg.duration_minutes > 0:
            speed = AVG_KMH_INFERENCE.get(leg.mode)
            if speed is None or speed <= 0:
                return None
            km = (leg.duration_minutes / 60.0) * speed
        if km is None or km <= 0:
            return None
        return km * factor

    def _enrich_deeplink_with_google_routes(self, options: list[DoorToDoorOptionOut]) -> list[DoorToDoorOptionOut]:
        reference_option = next(
            (
                option
                for option in options
                if any(source.provider == "google_routes" and source.source_type == "api" for source in option.sources)
            ),
            None,
        )
        if reference_option is None:
            return options

        reference_source = next(
            (
                source
                for source in reference_option.sources
                if source.provider == "google_routes" and source.source_type == "api"
            ),
            None,
        )
        if reference_source is None:
            return options

        outbound_reference, inbound_reference = self._split_ground_reference_legs(reference_option.legs)
        if outbound_reference is None and inbound_reference is None:
            return options

        merged: list[DoorToDoorOptionOut] = []
        for option in options:
            if option.status != "real_deeplink":
                merged.append(option)
                continue

            legs = [leg.model_copy(deep=True) for leg in option.legs]
            flight_index = next((index for index, leg in enumerate(legs) if leg.type == "flight"), -1)
            updated = False
            outbound_index: int | None = None

            if flight_index > 0 and outbound_reference is not None:
                for index in range(flight_index - 1, -1, -1):
                    if legs[index].type == "ground":
                        legs[index] = self._overlay_ground_leg(legs[index], outbound_reference)
                        outbound_index = index
                        updated = True
                        break

            if flight_index >= 0 and inbound_reference is not None:
                for index in range(flight_index + 1, len(legs)):
                    if legs[index].type == "ground":
                        legs[index] = self._overlay_ground_leg(legs[index], inbound_reference)
                        updated = True
                        break

            if not updated:
                merged.append(option)
                continue

            airport_buffer = option.airport_buffer_minutes
            if airport_buffer is None and outbound_index is not None and flight_index >= 0:
                outbound_arrival = legs[outbound_index].arrival_at
                flight_departure = legs[flight_index].departure_at
                if outbound_arrival is not None and flight_departure is not None:
                    diff_minutes = int((flight_departure - outbound_arrival).total_seconds() / 60)
                    if diff_minutes > 0:
                        airport_buffer = diff_minutes

            total_duration = option.total_duration_minutes
            if total_duration is None:
                leg_minutes = [
                    leg.duration_minutes
                    for leg in legs
                    if leg.type in {"ground", "flight"}
                ]
                if all(value is not None for value in leg_minutes):
                    total_duration = sum(int(value or 0) for value in leg_minutes) + int(airport_buffer or 0)

            sources = list(option.sources)
            if not any(source.provider == "google_routes" and source.source_type == "api" for source in sources):
                sources.append(
                    DoorToDoorSourceOut(
                        provider="google_routes",
                        source_provider="google_routes",
                        source_type="api",
                        confidence=reference_source.confidence,
                        checked_at=reference_source.checked_at,
                        expires_at=reference_source.expires_at,
                    )
                )

            source_types = list(option.source_types)
            if "api" not in source_types:
                source_types.append("api")

            merged.append(
                option.model_copy(
                    update={
                        "legs": legs,
                        "sources": sources,
                        "source_types": source_types,
                        "airport_buffer_minutes": airport_buffer,
                        "total_duration_minutes": total_duration,
                    }
                )
            )

        return merged

    def _split_ground_reference_legs(
        self,
        legs: list[DoorToDoorLegOut],
    ) -> tuple[DoorToDoorLegOut | None, DoorToDoorLegOut | None]:
        flight_index = next((index for index, leg in enumerate(legs) if leg.type == "flight"), -1)
        if flight_index < 0:
            return None, None

        outbound: DoorToDoorLegOut | None = None
        inbound: DoorToDoorLegOut | None = None
        for index, leg in enumerate(legs):
            if leg.type != "ground":
                continue
            if leg.duration_minutes is None:
                continue
            if index < flight_index:
                outbound = leg
            elif index > flight_index and inbound is None:
                inbound = leg
        return outbound, inbound

    def _overlay_ground_leg(self, base_leg: DoorToDoorLegOut, route_leg: DoorToDoorLegOut) -> DoorToDoorLegOut:
        return base_leg.model_copy(
            update={
                "departure_at": route_leg.departure_at or base_leg.departure_at,
                "arrival_at": route_leg.arrival_at or base_leg.arrival_at,
                "duration_minutes": route_leg.duration_minutes if route_leg.duration_minutes is not None else base_leg.duration_minutes,
                "distance_meters": route_leg.distance_meters if route_leg.distance_meters is not None else base_leg.distance_meters,
                "source_type": "api",
                "confidence": route_leg.confidence or base_leg.confidence,
            }
        )

    def _option_matches_modes(self, option: DoorToDoorOptionOut, preferences: DoorToDoorPreferences) -> bool:
        allowed_modes = self._allowed_ground_modes(preferences)
        if not allowed_modes:
            return False
        for leg in option.legs:
            if leg.type == "ground" and leg.mode in GROUND_MODES and leg.mode not in allowed_modes:
                return False
        return True

    def _allowed_ground_modes(self, preferences: DoorToDoorPreferences) -> set[DoorToDoorMode]:
        if preferences.public_transport_only:
            return {"bus", "train", "walking"}
        allowed: set[DoorToDoorMode] = {"walking"}
        if preferences.allow_bus:
            allowed.add("bus")
        if preferences.allow_train:
            allowed.add("train")
        if preferences.allow_rideshare:
            allowed.add("rideshare")
        if preferences.allow_shuttle:
            allowed.add("shuttle")
        if preferences.allow_taxi:
            allowed.add("taxi")
        if preferences.allow_car:
            allowed.add("car")
        return allowed

    # ------------------------------------------------------------------
    # Fase 6: cross-provider arbitration
    # ------------------------------------------------------------------

    @staticmethod
    def _leg_source_quality(leg: DoorToDoorLegOut) -> int:
        """Rate a ground leg's source quality. Higher = better data.

        Real data with duration and schedule from high-quality sources
        scores highest. Deeplinks and estimates score lower.
        """
        if leg.type != "ground":
            return -1
        base = SOURCE_QUALITY.get(leg.source_type or "estimate", 0)
        # Bonus for having concrete data (duration + schedule)
        if leg.duration_minutes is not None:
            base += 2
        if leg.departure_at is not None and leg.arrival_at is not None:
            base += 1
        return base

    @staticmethod
    def _best_ground_leg(
        legs: list[DoorToDoorLegOut],
    ) -> DoorToDoorLegOut | None:
        """Pick the best ground leg from a list by source quality."""
        ground = [leg for leg in legs if leg.type == "ground"]
        if not ground:
            return None
        ground.sort(key=lambda leg: DoorToDoorSearchService._leg_source_quality(leg), reverse=True)
        return ground[0]

    @staticmethod
    def _extract_outbound_legs(options: list[DoorToDoorOptionOut]) -> list[DoorToDoorLegOut]:
        """Extract outbound ground legs (before the flight) from all options."""
        legs: list[DoorToDoorLegOut] = []
        for option in options:
            flight_idx = next((i for i, leg in enumerate(option.legs) if leg.type == "flight"), -1)
            if flight_idx < 0:
                continue
            for i in range(flight_idx):
                if option.legs[i].type == "ground":
                    legs.append(option.legs[i])
        return legs

    @staticmethod
    def _extract_inbound_legs(options: list[DoorToDoorOptionOut]) -> list[DoorToDoorLegOut]:
        """Extract inbound ground legs (after the flight) from all options."""
        legs: list[DoorToDoorLegOut] = []
        for option in options:
            flight_idx = next((i for i, leg in enumerate(option.legs) if leg.type == "flight"), -1)
            if flight_idx < 0:
                continue
            for i in range(flight_idx + 1, len(option.legs)):
                if option.legs[i].type == "ground":
                    legs.append(option.legs[i])
        return legs

    def _compose_cross_provider(
        self,
        options: list[DoorToDoorOptionOut],
        flight: DoorToDoorFlightOut,
        query: DoorToDoorProviderQuery,
    ) -> DoorToDoorOptionOut | None:
        """Create a composite option using the best outbound and best inbound
        ground legs, potentially from different providers.

        Only creates a composite when both legs carry real data (source quality >= 2)
        and at least one leg improves over what the best single-provider option offers.
        """
        if len(options) < 2:
            return None

        outbound_legs = self._extract_outbound_legs(options)
        inbound_legs = self._extract_inbound_legs(options)
        if not outbound_legs or not inbound_legs:
            return None

        best_outbound = self._best_ground_leg(outbound_legs)
        best_inbound = self._best_ground_leg(inbound_legs)
        if best_outbound is None or best_inbound is None:
            return None

        # Only compose if both legs have real data (quality >= sources like maps/deeplink)
        out_quality = self._leg_source_quality(best_outbound)
        in_quality = self._leg_source_quality(best_inbound)
        if out_quality < 3 or in_quality < 3:
            return None

        # Check if the best single-provider option already has both these legs
        # (avoid creating a duplicate composite)
        best_option = max(options, key=lambda o: o.score or 0)
        best_opt_outbound = self._best_ground_leg(
            [leg for leg in best_option.legs if leg.type == "ground"],
        )
        best_opt_inbound = self._best_ground_leg(
            [leg for leg in best_option.legs if leg.type == "ground"],
        )

        same_outbound = best_opt_outbound and best_outbound.provider == best_opt_outbound.provider
        same_inbound = best_opt_inbound and best_inbound.provider == best_opt_inbound.provider
        if same_outbound and same_inbound:
            return None  # Best single option already has the best legs

        # Build the composite option
        flight_duration = int((flight.arrival_at - flight.departure_at).total_seconds() / 60)
        airport_buffer = max(query.preferences.min_airport_buffer_minutes, 90)

        # Collect unique sources from both legs
        sources: list[DoorToDoorSourceOut] = []
        source_types: list[DoorToDoorSourceType] = []
        seen_providers: set[str] = set()
        for leg in (best_outbound, best_inbound):
            provider = leg.provider or "composite"
            if provider not in seen_providers:
                seen_providers.add(provider)
                st = leg.source_type or "api"
                sources.append(DoorToDoorSourceOut(
                    provider=provider,
                    source_provider=provider,
                    source_type=st,
                    confidence=leg.confidence or "estimated",
                    checked_at=query.checked_at,
                    expires_at=query.checked_at + timedelta(hours=6),
                ))
                if st not in source_types:
                    source_types.append(st)

        # Build legs: outbound ground → flight → inbound ground
        legs: list[DoorToDoorLegOut] = [
            best_outbound.model_copy(deep=True),
            DoorToDoorLegOut(
                type="flight",
                mode="flight",
                from_location=flight.origin_airport,
                to_location=flight.destination_airport,
                departure_at=flight.departure_at,
                arrival_at=flight.arrival_at,
                duration_minutes=flight_duration,
                provider="flight_watch",
                source_type="api",
                confidence=flight.flight_time_confidence,
            ),
            best_inbound.model_copy(deep=True),
        ]

        ground_duration = (best_outbound.duration_minutes or 0) + (best_inbound.duration_minutes or 0)
        total_duration = ground_duration + airport_buffer + flight_duration

        # Score the composite (uses source_quality_bonus for best-of-breed legs)
        score = score_itinerary(
            price_midpoint=None,
            duration_minutes=total_duration,
            airport_buffer_minutes=airport_buffer,
            transfer_count=2,
            confidence="live",
            completeness="full",
            source_quality_bonus=8,  # Best-of-breed composition bonus
        )

        out_label = best_outbound.provider or ""
        in_label = best_inbound.provider or ""

        return DoorToDoorOptionOut(
            id="option_composite_0",
            label=f"Mejor combinacion ({out_label} + {in_label})",
            description="Combinacion optima de fuentes: el mejor tramo de ida y de vuelta de distintos proveedores.",
            status="real_result",
            total_price_min=None,
            total_price_max=None,
            price_per_person_min=None,
            price_per_person_max=None,
            currency="EUR",
            total_duration_minutes=total_duration,
            score=score,
            transfer_count=2,
            airport_buffer_minutes=airport_buffer,
            confidence="live",
            source_types=source_types,
            sources=sources,
            legs=legs,
            is_extended=False,
            deep_link=None,
            price=None,
            trust_copy="Combinacion de los mejores datos disponibles de transporte publico. Sin precio confirmado.",
        )

    def _sort_options(self, options: list[DoorToDoorOptionOut], sort_by: DoorToDoorSortBy) -> list[DoorToDoorOptionOut]:
        # Primary: completeness, then status, then source quality, then sort criteria
        completeness_order = {"full": 0, "partial_actionable": 1, "exploratory": 2}
        status_order = {"real_result": 0, "real_deeplink": 1, "estimate_only": 2}

        def _source_quality_rank(item: DoorToDoorOptionOut) -> int:
            """Best source type among the option's sources (lower = better rank)."""
            best = max((SOURCE_QUALITY.get(st, 0) for st in item.source_types), default=0)
            return -best  # negative so higher quality sorts first

        def _sort_key(item: DoorToDoorOptionOut):
            comp_rank = completeness_order.get(item.completeness, 2)
            status_rank = status_order.get(item.status, 2)
            quality_rank = _source_quality_rank(item)
            if sort_by == "cheapest":
                return (comp_rank, status_rank, quality_rank, item.total_price_min is None, item.total_price_min or 10_000)
            if sort_by == "fastest":
                has_duration = item.total_duration_minutes is None
                return (comp_rank, status_rank, quality_rank, has_duration, item.total_duration_minutes or 999_999)
            if sort_by == "fewest_changes":
                return (comp_rank, status_rank, quality_rank, item.transfer_count, -(item.score or 0))
            if sort_by == "lowest_emissions":
                # Eco route: missing totals (None) sink to the bottom so users
                # see only options we could actually estimate. `float('inf')`
                # keeps the intent explicit (always larger than any finite kg).
                has_total = item.total_co2_kg is None
                return (
                    comp_rank,
                    status_rank,
                    quality_rank,
                    has_total,
                    item.total_co2_kg if item.total_co2_kg is not None else float("inf"),
                )
            # best_balance: sort by score descending within completeness groups
            return (comp_rank, status_rank, quality_rank, -(item.score or 0))

        return sorted(options, key=_sort_key)

    def _append_warning(
        self,
        warnings: list[DoorToDoorWarningOut],
        warning: DoorToDoorWarningOut,
    ) -> None:
        exists = any(
            current.code == warning.code and current.provider == warning.provider
            for current in warnings
        )
        if not exists:
            warnings.append(warning)

    def _store_history(
        self,
        db: Session,
        user_id: str,
        request: DoorToDoorSearchRequest,
        summary: DoorToDoorSummaryOut,
        options: list[DoorToDoorOptionOut],
        warnings: list[DoorToDoorWarningOut],
    ) -> DoorToDoorSearchHistory:
        recommended = next((option for option in options if option.id == summary.recommended_option_id), None)
        summary_payload = {
            "recommended_option_id": summary.recommended_option_id,
            "cheapest_option_id": summary.cheapest_option_id,
            "options_count": len(options),
            "recommended": recommended.model_dump(mode="json", by_alias=True) if recommended else None,
        }
        history = DoorToDoorSearchHistory(
            user_id=user_id,
            watch_id=request.flight_watch_id,
            origin_json=json.dumps(request.origin.model_dump(mode="json"), ensure_ascii=False),
            final_destination_json=json.dumps(request.final_destination.model_dump(mode="json"), ensure_ascii=False),
            preferences_json=json.dumps(request.preferences.model_dump(mode="json"), ensure_ascii=False),
            summary_json=json.dumps(summary_payload, ensure_ascii=False),
            warnings_json=json.dumps([warning.model_dump(mode="json") for warning in warnings], ensure_ascii=False),
        )
        db.add(history)
        db.commit()
        db.refresh(history)
        return history

    def _prune_old_history(self, db: Session, user_id: str) -> None:
        cutoff = utc_now_naive() - timedelta(days=90)
        old_items = list(
            db.scalars(
                select(DoorToDoorSearchHistory).where(
                    DoorToDoorSearchHistory.user_id == user_id,
                    DoorToDoorSearchHistory.created_at < cutoff,
                    DoorToDoorSearchHistory.is_saved == False,  # noqa: E712 — never prune saved plans
                )
            )
        )
        for item in old_items:
            db.delete(item)
        if old_items:
            db.commit()
