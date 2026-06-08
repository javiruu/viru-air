import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import (
    DoorToDoorFlightOut,
    DoorToDoorLegOut,
    DoorToDoorMode,
    DoorToDoorOptionOut,
    DoorToDoorPreferences,
    DoorToDoorProviderStatusOut,
    DoorToDoorSearchRequest,
    DoorToDoorSearchResponse,
    DoorToDoorSortBy,
    DoorToDoorSourceOut,
    DoorToDoorSummaryOut,
    DoorToDoorWarningOut,
)
from app.door_to_door.services.itinerary_builder import build_summary
from app.infrastructure.db.models import DoorToDoorChosenOption, DoorToDoorSearchHistory

logger = logging.getLogger("app.door_to_door")

GROUND_MODES: set[DoorToDoorMode] = {"bus", "train", "rideshare", "shuttle", "taxi", "car", "walking"}


class DoorToDoorSearchService:
    def __init__(
        self,
        providers: list[DoorToDoorProvider] | None = None,
        provider_statuses: list[DoorToDoorProviderStatusOut] | None = None,
        mock_enabled: bool = False,
    ) -> None:
        self.providers = providers or []
        self.provider_statuses = provider_statuses or []
        self.mock_enabled = mock_enabled

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
        warnings: list[DoorToDoorWarningOut] = list(bootstrap_warnings or [])
        options: list[DoorToDoorOptionOut] = []

        for provider in self.providers:
            try:
                provider_options = await provider.run_search(query)
                options.extend(provider_options)
                for warning in provider.consume_warnings():
                    self._append_warning(warnings, warning)
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
                        code="PARTIAL_PROVIDER_COVERAGE",
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
        options, filter_warnings = self._apply_preferences(options, request.preferences)
        warnings.extend(filter_warnings)

        if options:
            if self.mock_enabled or any("estimate" in option.source_types or "mock" in option.source_types for option in options):
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

        return DoorToDoorSearchResponse(flight=flight, summary=summary, options=options, warnings=warnings)

    def _has_enabled_real_search_provider(self) -> bool:
        for item in self.provider_statuses:
            if item.enabled and item.source_type not in ("mock", "estimate") and item.supports_search:
                return True
        return False

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

    def _sort_options(self, options: list[DoorToDoorOptionOut], sort_by: DoorToDoorSortBy) -> list[DoorToDoorOptionOut]:
        # Always put estimate_only last, then sort by the requested criteria
        status_order = {"real_result": 0, "real_deeplink": 1, "estimate_only": 2}

        def _sort_key(item: DoorToDoorOptionOut):
            status_rank = status_order.get(item.status, 2)
            if sort_by == "cheapest":
                return (status_rank, item.total_price_min is None, item.total_price_min or 10_000)
            if sort_by == "fastest":
                has_duration = item.total_duration_minutes is None
                return (status_rank, has_duration, item.total_duration_minutes or 999_999)
            if sort_by == "fewest_changes":
                return (status_rank, item.transfer_count, -(item.score or 0))
            # best_balance: sort by score descending within status groups
            return (status_rank, -(item.score or 0))

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
                )
            )
        )
        for item in old_items:
            db.delete(item)
        if old_items:
            db.commit()
