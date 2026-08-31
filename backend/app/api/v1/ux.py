from __future__ import annotations

import json
import logging
from collections.abc import Mapping

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import ClientErrorIn, UxEventIn
from app.infrastructure.db.models import ClientErrorEvent, User, UxEvent
from app.infrastructure.db.session import get_db

router = APIRouter()
logger = logging.getLogger("app.ux")

ALLOWED_EVENTS = {
    "dashboard_view",
    "quick_search_executed",
    "watchlist_refresh",
    "alert_created",
    "alert_triggered",
    "search_empty_results",
    "hotel_rum_vitals",
    "hotel_search_completed",
    "hotel_detail_viewed",
    "hotel_tracking_created",
    "hotel_alert_created",
    "hotel_inbox_viewed",
    "hotel_partner_clicked",
}
HOTEL_RUM_METADATA_KEYS: set[str] = {
    "schema_version",
    "surface",
    "metric",
    "value_bucket",
    "rating",
    "navigation_type",
    "device_class",
}
HOTEL_RUM_ALLOWED_VALUES: dict[str, set[object]] = {
    "schema_version": {1},
    "surface": {"hoteles"},
    "metric": {"lcp", "inp", "cls", "ttfb"},
    "rating": {"good", "needs_improvement", "poor"},
    "navigation_type": {"navigate", "reload", "back_forward", "prerender"},
    "device_class": {"mobile", "tablet", "desktop"},
}
HOTEL_RUM_ALLOWED_BUCKETS: set[str] = {
    "0-250ms", "250-500ms", "500-1000ms", "1000-2000ms", "2000-4000ms", "4000-8000ms", "8000+ms",
    "0-0.1", "0.1-0.25", "0.25-0.5", "0.5+", "unknown",
}

# Product events use the same bounded, non-PII contract as RUM. IDs, URLs,
# emails, provider payloads and arbitrary metadata are deliberately excluded.
HOTEL_PRODUCT_EVENT_METADATA: dict[str, dict[str, set[object]]] = {
    "hotel_search_completed": {
        "schema_version": {1},
        "surface": {"hoteles"},
        "result_state": {"success", "empty", "partial", "stale", "error"},
        "result_count_bucket": {"0", "1-3", "4-10", "11+"},
        "provider_mode": {"mock", "manual", "commercial", "unknown"},
    },
    "hotel_detail_viewed": {
        "schema_version": {1},
        "surface": {"hoteles"},
        "detail_state": {"success", "partial", "stale", "unavailable", "not_found", "error"},
    },
    "hotel_tracking_created": {
        "schema_version": {1},
        "surface": {"hoteles"},
        "tracking_state": {"active", "pending_context", "pending_first_observation", "partial", "unavailable"},
    },
    "hotel_alert_created": {
        "schema_version": {1},
        "surface": {"hoteles"},
        "alert_type": {"price_below", "price_above", "percentage_drop", "percentage_increase", "provider_changed", "availability_returned", "parity_break"},
    },
    "hotel_inbox_viewed": {
        "schema_version": {1},
        "surface": {"hoteles", "notifications"},
        "unread_bucket": {"0", "1-3", "4-10", "11+"},
    },
    "hotel_partner_clicked": {
        "schema_version": {1},
        "surface": {"hoteles"},
        "disclosure_state": {"shown", "not_applicable", "blocked"},
    },
}

HOTEL_PRODUCT_EVENT_NAMES = set(HOTEL_PRODUCT_EVENT_METADATA)


def _hotel_product_metadata_is_valid(event_name: str, metadata: Mapping[str, object]) -> bool:
    allowed = HOTEL_PRODUCT_EVENT_METADATA.get(event_name)
    if allowed is None or set(metadata) != set(allowed):
        return False
    if type(metadata.get("schema_version")) is not int:
        return False
    return all(metadata.get(key) in values for key, values in allowed.items())


def _hotel_event_is_allowed(event_name: str, metadata: Mapping[str, object]) -> bool:
    if event_name == "hotel_rum_vitals":
        return True
    if event_name in HOTEL_PRODUCT_EVENT_NAMES:
        return _hotel_product_metadata_is_valid(event_name, metadata)
    return True


@router.post("/events")
def create_ux_event(
    payload: UxEventIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    event_name = payload.event_name.strip()
    if event_name not in ALLOWED_EVENTS:
        return {"status": "ignored"}
    if event_name == "hotel_rum_vitals":
        metadata = payload.metadata
        if set(metadata) != HOTEL_RUM_METADATA_KEYS:
            return {"status": "ignored"}
        schema_version = metadata.get("schema_version")
        if type(schema_version) is not int or schema_version != 1:
            return {"status": "ignored"}
        if any(metadata.get(key) not in allowed for key, allowed in HOTEL_RUM_ALLOWED_VALUES.items() if key != "schema_version"):
            return {"status": "ignored"}
        value_bucket = metadata.get("value_bucket")
        if value_bucket not in HOTEL_RUM_ALLOWED_BUCKETS:
            return {"status": "ignored"}
        metric = metadata.get("metric")
        if metric == "cls" and value_bucket not in {"0-0.1", "0.1-0.25", "0.25-0.5", "0.5+", "unknown"}:
            return {"status": "ignored"}
        if metric != "cls" and value_bucket not in {"0-250ms", "250-500ms", "500-1000ms", "1000-2000ms", "2000-4000ms", "4000-8000ms", "8000+ms", "unknown"}:
            return {"status": "ignored"}
    elif event_name in HOTEL_PRODUCT_EVENT_NAMES and not _hotel_event_is_allowed(event_name, payload.metadata):
        return {"status": "ignored"}

    event = UxEvent(
        user_id=current_user.id,
        event_name=event_name,
        duration_ms=payload.duration_ms,
        metadata_json=json.dumps(payload.metadata, ensure_ascii=False) if payload.metadata else None,
    )
    db.add(event)
    db.commit()
    return {"status": "ok"}


@router.post("/errors")
def create_client_error(
    payload: ClientErrorIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    logger.error(
        "client_error section=%s user_id=%s message=%s stack=%s",
        payload.section,
        current_user.id,
        payload.message,
        payload.stack or "",
    )
    db.add(
        ClientErrorEvent(
            user_id=current_user.id,
            section=payload.section,
            message=payload.message,
            stack=payload.stack,
        )
    )
    db.commit()
    return {"status": "logged"}
