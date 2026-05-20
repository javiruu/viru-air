import json
import logging
from datetime import datetime, timedelta

from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.providers.mock import MockDoorToDoorProvider
from app.door_to_door.schemas import (
    DoorToDoorFlightOut,
    DoorToDoorOptionOut,
    DoorToDoorSearchRequest,
    DoorToDoorSearchResponse,
    DoorToDoorSummaryOut,
    DoorToDoorWarningOut,
)
from app.door_to_door.services.itinerary_builder import build_summary
from app.core.time import utc_now_naive
from app.infrastructure.db.models import DoorToDoorChosenOption, DoorToDoorSearchHistory
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger("app.door_to_door")


class DoorToDoorSearchService:
    def __init__(self, providers: list[DoorToDoorProvider] | None = None) -> None:
        self.providers = providers or [MockDoorToDoorProvider()]

    async def search(
        self,
        *,
        db: Session,
        user_id: str,
        request: DoorToDoorSearchRequest,
        flight: DoorToDoorFlightOut,
    ) -> DoorToDoorSearchResponse:
        checked_at = datetime.now(tz=flight.departure_at.tzinfo)
        query = DoorToDoorProviderQuery(
            origin=request.origin,
            final_destination=request.final_destination,
            preferences=request.preferences,
            flight=flight,
            checked_at=checked_at,
        )
        warnings: list[DoorToDoorWarningOut] = []
        options: list[DoorToDoorOptionOut] = []
        for provider in self.providers:
            try:
                provider_options = await provider.run_search(query)
                options.extend(provider_options)
            except Exception as exc:
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
                warnings.append(
                    DoorToDoorWarningOut(
                        code="PARTIAL_PROVIDER_COVERAGE",
                        provider=provider.provider_name,
                        message="Una fuente no ha respondido a tiempo. Te mostramos las opciones con datos suficientes.",
                    )
                )
        if options:
            warnings.append(
                DoorToDoorWarningOut(
                    code="ESTIMATED_MOCK_DATA",
                    message="V1 usa datos mock estimados mientras se conectan APIs y fuentes reales.",
                )
            )
        else:
            warnings.append(
                DoorToDoorWarningOut(
                    code="NO_COVERAGE",
                    message="No hay datos suficientes para montar una ruta completa con estos filtros.",
                )
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
        if chosen:
            summary.chosen_option_id = chosen.option_id
        history = self._store_history(db, user_id, request, summary, options, warnings)
        summary.history_id = history.id
        self._prune_old_history(db, user_id)
        return DoorToDoorSearchResponse(flight=flight, summary=summary, options=options, warnings=warnings)

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
