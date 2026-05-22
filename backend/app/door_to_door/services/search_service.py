import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import (
    DoorToDoorFlightOut,
    DoorToDoorMode,
    DoorToDoorOptionOut,
    DoorToDoorPreferences,
    DoorToDoorProviderStatusOut,
    DoorToDoorSearchRequest,
    DoorToDoorSearchResponse,
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
                self._append_warning(
                    warnings,
                    DoorToDoorWarningOut(
                        code="PROVIDER_PARTIAL_COVERAGE",
                        provider=provider.provider_name,
                        message="Proveedor con cobertura parcial en esta consulta.",
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

        options, filter_warnings = self._apply_preferences(options, request.preferences)
        warnings.extend(filter_warnings)

        if options:
            if self.mock_enabled or any("mock" in option.source_types for option in options):
                self._append_warning(
                    warnings,
                    DoorToDoorWarningOut(
                        code="ESTIMATED_MOCK_DATA",
                        message="Algunas rutas usan datos mock estimados mientras se conectan fuentes reales.",
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
            if item.enabled and item.source_type != "mock" and item.supports_search:
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

    def _sort_options(self, options: list[DoorToDoorOptionOut], sort_by: str) -> list[DoorToDoorOptionOut]:
        if sort_by == "cheapest":
            return sorted(options, key=lambda item: (item.total_price_min is None, item.total_price_min or 10_000))
        if sort_by == "lowest_risk":
            risk_order = {"low": 0, "medium": 1, "unknown": 2, "high": 3}
            return sorted(options, key=lambda item: (risk_order[item.risk_level], -item.score))
        if sort_by == "fastest":
            return sorted(options, key=lambda item: item.total_duration_minutes)
        if sort_by == "fewest_changes":
            return sorted(options, key=lambda item: (item.transfer_count, -item.score))
        return sorted(options, key=lambda item: item.score, reverse=True)

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
            "lowest_risk_option_id": summary.lowest_risk_option_id,
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
