import json
from datetime import date as Date, datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.domain.schemas import (
    HotelAlertEventOut,
    HotelAlertRuleCreateIn,
    HotelAlertRuleOut,
    HotelAlertRuleUpdateIn,
    HotelAreaResolveOut,
    HotelAreaResolveQueryIn,
    HotelAreaSearchQueryIn,
    HotelAreaSearchResultOut,
    HotelV2AreaSearchOut,
    HotelV2AreaSearchResultOut,
    HotelV2FreshnessOut,
    HotelV2HistoryAggregatesOut,
    HotelV2HistoryIdentityOut,
    HotelV2HistoryPointOut,
    HotelV2HistorySeriesOut,
    HotelV2PaginationOut,
    HotelV2PriceOut,
    HotelV2ProviderOut,
    HotelV2ResultExplanationOut,
    HotelV2ResultsMetaOut,
    HotelV2StayContextOut,
    HotelV2TrackedOfferOut,
    HotelV2TrackedOfferCreateIn,
    HotelV2TrackedOfferCreateOut,
    HotelV2TrackedOfferCreationMetaOut,
    HotelV2TrackedOfferLifecycleIn,
    HotelV2TrackedOfferLifecycleOut,
    HotelV2TrackedOfferHistoryOut,
    HotelV2TrackedOffersMetaOut,
    HotelV2TrackedOffersOut,
    HotelV2TrackingObservationOut,
    HotelV2TrackingStayContextOut,
    HotelV2WarningOut,
    HotelCompSetCreateIn,
    HotelCompSetDetailOut,
    HotelCompSetMemberCreateIn,
    HotelCompSetMemberOut,
    HotelNearbySuggestionOut,
    HotelCompSetOut,
    HotelDetailOut,
    HotelIngestOut,
    HotelParityOut,
    HotelProviderRunOut,
    HotelRateOut,
    HotelRatesQueryIn,
    HotelSearchOut,
    HotelSearchQueryIn,
    HotelSavedSearchCreateIn,
    HotelSavedSearchOut,
    HotelSavedSearchUpdateIn,
    HotelTrackedOfferCreateIn,
    HotelTrackedOfferOut,
    HotelTrackedOfferUpdateIn,
    HotelWatchlistItemCreateIn,
    HotelWatchlistItemOut,
)
from app.infrastructure.db.models import HotelRateSnapshot, HotelTrackedOffer, User
from app.infrastructure.db.session import get_db
from app.core.request_context import get_correlation_id
from app.hotels.activation import resolve_hotel_activation
from app.hotels.partner_links import sanitize_hotel_deep_link
from app.services import hotels_service

router = APIRouter()


def _extract_validation_error_code(exc: ValidationError) -> str:
    first_error = exc.errors()[0] if exc.errors() else {}
    msg = first_error.get("msg")
    if isinstance(msg, str) and msg:
        prefix = "Value error, "
        if msg.startswith(prefix):
            return msg[len(prefix) :]
        return msg
    ctx = first_error.get("ctx")
    if isinstance(ctx, dict):
        err = ctx.get("error")
        if isinstance(err, ValueError):
            return str(err)
    return "validation_error"


def _raise_http_for_value_error(exc: ValueError) -> None:
    code = str(exc)
    if code in {
        "hotel_not_found",
        "hotel_provider_run_not_found",
        "hotel_watchlist_item_not_found",
        "hotel_comp_set_not_found",
        "hotel_comp_set_member_not_found",
        "hotel_alert_rule_not_found",
        "tracked_offer_not_found",
        "hotel_saved_search_not_found",
        "area_not_found",
        "hotel_source_rate_not_found",
    }:
        raise HTTPException(status_code=404, detail=code) from exc
    if code in {
        "hotel_watchlist_item_already_exists",
        "hotel_comp_set_member_already_exists",
        "hotel_comp_set_anchor_cannot_be_member",
        "tracked_offer_already_exists",
        "tracked_offer_state_conflict",
    }:
        raise HTTPException(status_code=409, detail=code) from exc
    raise HTTPException(status_code=422, detail=code) from exc


def _raise_http_for_permission_error(exc: PermissionError) -> None:
    raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/search", response_model=list[HotelSearchOut])
def search_hotels(
    q: str | None = Query(default=None, max_length=120),
    city: str | None = Query(default=None, max_length=100),
    country_code: str | None = Query(default=None, max_length=2),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[HotelSearchOut]:
    try:
        query = HotelSearchQueryIn(
            q=q,
            city=city,
            country_code=country_code,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_extract_validation_error_code(exc)) from exc

    rows = hotels_service.search_hotels(
        db,
        q=query.q,
        city=query.city,
        country_code=query.country_code,
        limit=query.limit,
        offset=query.offset,
    )
    return [
        HotelSearchOut(
            id=row.id,
            canonical_name=row.canonical_name,
            city=row.city,
            country_code=row.country_code,
            stars=row.stars,
        )
        for row in rows
    ]


@router.post("/ingest/mock", response_model=HotelIngestOut)
def ingest_hotels_mock(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> HotelIngestOut:
    try:
        result = hotels_service.ingest_hotels_mock(db)
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    return HotelIngestOut(
        provider_id=result.provider_id,
        hotels_processed=result.hotels_processed,
        rates_ingested=result.rates_ingested,
        ambiguous_matches=result.ambiguous_matches,
        warnings=result.warnings,
        needs_review=result.needs_review,
        provider_run_id=result.provider_run_id,
    )


@router.get("/provider-runs/{provider_run_id}", response_model=HotelProviderRunOut)
def get_hotel_provider_run(
    provider_run_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> HotelProviderRunOut:
    try:
        row = hotels_service.get_hotel_provider_run_or_404(db, provider_run_id)
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    return HotelProviderRunOut(
        id=row.id,
        provider=row.provider,
        correlation_id=row.correlation_id,
        client_event_id=row.client_event_id,
        execution_id=row.execution_id,
        started_at=row.started_at,
        finished_at=row.finished_at,
        status=row.status,
        items_processed=row.items_processed,
        error_message=hotels_service._sanitize_hotel_error(row.error_message) if row.error_message else None,
        tracked_outcomes=row.tracked_outcomes,
    )


@router.get("/watchlist", response_model=list[HotelWatchlistItemOut])
def list_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HotelWatchlistItemOut]:
    rows = hotels_service.list_watchlist(db, current_user.id)
    return [HotelWatchlistItemOut(id=row.id, hotel_id=row.hotel_id, label=row.label, created_at=row.created_at) for row in rows]


@router.post("/watchlist", response_model=HotelWatchlistItemOut)
def create_watchlist_item(
    payload: HotelWatchlistItemCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelWatchlistItemOut:
    try:
        row = hotels_service.add_watchlist_item(db, user_id=current_user.id, hotel_id=payload.hotel_id, label=payload.label)
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    return HotelWatchlistItemOut(id=row.id, hotel_id=row.hotel_id, label=row.label, created_at=row.created_at)


@router.delete("/watchlist/{item_id}")
def delete_watchlist_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    try:
        hotels_service.delete_watchlist_item(db, user_id=current_user.id, item_id=item_id)
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return {"status": "ok"}


def _saved_search_out(row: object) -> HotelSavedSearchOut:
    return HotelSavedSearchOut(
        id=row.id,
        user_id=row.user_id,
        schema_version=row.schema_version,
        fingerprint=row.fingerprint,
        query=json.loads(row.canonical_query_json),
        label=row.label,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_used_at=row.last_used_at,
    )


@router.get("/saved-searches", response_model=list[HotelSavedSearchOut])
def list_saved_searches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HotelSavedSearchOut]:
    return [_saved_search_out(row) for row in hotels_service.list_saved_hotel_searches(db, user_id=current_user.id)]


@router.post("/saved-searches", response_model=HotelSavedSearchOut, status_code=201)
def create_saved_search(
    payload: HotelSavedSearchCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelSavedSearchOut:
    try:
        row = hotels_service.create_saved_hotel_search(
            db,
            user_id=current_user.id,
            schema_version=payload.schema_version,
            query=payload.query,
            label=payload.label,
        )
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    return _saved_search_out(row)


@router.get("/saved-searches/{saved_search_id}", response_model=HotelSavedSearchOut)
def get_saved_search(
    saved_search_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelSavedSearchOut:
    try:
        row = hotels_service.get_saved_hotel_search_or_404(db, user_id=current_user.id, saved_search_id=saved_search_id)
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return _saved_search_out(row)


@router.patch("/saved-searches/{saved_search_id}", response_model=HotelSavedSearchOut)
def update_saved_search(
    saved_search_id: str,
    payload: HotelSavedSearchUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelSavedSearchOut:
    try:
        row = hotels_service.update_saved_hotel_search(
            db,
            user_id=current_user.id,
            saved_search_id=saved_search_id,
            update_data=payload.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return _saved_search_out(row)


@router.delete("/saved-searches/{saved_search_id}")
def delete_saved_search(
    saved_search_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    try:
        hotels_service.delete_saved_hotel_search(db, user_id=current_user.id, saved_search_id=saved_search_id)
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return {"status": "ok"}


@router.get("/comp-sets", response_model=list[HotelCompSetOut])
def list_comp_sets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HotelCompSetOut]:
    rows = hotels_service.list_comp_sets(db, current_user.id)
    return [HotelCompSetOut(id=row.id, name=row.name, anchor_hotel_id=row.anchor_hotel_id, created_at=row.created_at) for row in rows]


@router.post("/comp-sets", response_model=HotelCompSetOut)
def create_comp_set(
    payload: HotelCompSetCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelCompSetOut:
    try:
        row = hotels_service.create_comp_set(
            db,
            user_id=current_user.id,
            name=payload.name,
            anchor_hotel_id=payload.anchor_hotel_id,
        )
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    return HotelCompSetOut(id=row.id, name=row.name, anchor_hotel_id=row.anchor_hotel_id, created_at=row.created_at)


@router.get("/comp-sets/{comp_set_id}", response_model=HotelCompSetDetailOut)
def get_comp_set_detail(
    comp_set_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelCompSetDetailOut:
    try:
        comp_set = hotels_service.get_comp_set_or_404(db, user_id=current_user.id, comp_set_id=comp_set_id)
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)

    members = hotels_service.list_comp_set_members(db, comp_set_id)
    return HotelCompSetDetailOut(
        id=comp_set.id,
        name=comp_set.name,
        anchor_hotel_id=comp_set.anchor_hotel_id,
        created_at=comp_set.created_at,
        members=[HotelCompSetMemberOut(id=m.id, comp_set_id=m.comp_set_id, hotel_id=m.hotel_id) for m in members],
    )


@router.get("/comp-sets/{comp_set_id}/nearby-suggestions", response_model=list[HotelNearbySuggestionOut])
def get_comp_set_nearby_suggestions(
    comp_set_id: str,
    radius_km: int = Query(default=5, ge=1, le=50),
    limit: int = Query(default=6, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HotelNearbySuggestionOut]:
    try:
        suggestions = hotels_service.get_nearby_comp_set_suggestions(
            db,
            user_id=current_user.id,
            comp_set_id=comp_set_id,
            radius_km=radius_km,
            limit=limit,
        )
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)

    return [
        HotelNearbySuggestionOut(
            hotel_id=item.hotel_id,
            canonical_name=item.canonical_name,
            city=item.city,
            country_code=item.country_code,
            stars=item.stars,
            distance_km=item.distance_km,
        )
        for item in suggestions
    ]


@router.post("/comp-sets/{comp_set_id}/members", response_model=HotelCompSetMemberOut)
def add_comp_set_member(
    comp_set_id: str,
    payload: HotelCompSetMemberCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelCompSetMemberOut:
    try:
        member = hotels_service.add_comp_set_member(
            db,
            user_id=current_user.id,
            comp_set_id=comp_set_id,
            hotel_id=payload.hotel_id,
        )
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return HotelCompSetMemberOut(id=member.id, comp_set_id=member.comp_set_id, hotel_id=member.hotel_id)


@router.delete("/comp-sets/{comp_set_id}/members/{member_id}")
def delete_comp_set_member(
    comp_set_id: str,
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    try:
        hotels_service.delete_comp_set_member(
            db,
            user_id=current_user.id,
            comp_set_id=comp_set_id,
            member_id=member_id,
        )
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return {"status": "ok"}


@router.delete("/comp-sets/{comp_set_id}")
def delete_comp_set(
    comp_set_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    try:
        hotels_service.delete_comp_set(db, user_id=current_user.id, comp_set_id=comp_set_id)
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return {"status": "ok"}


@router.get("/alert-rules", response_model=list[HotelAlertRuleOut])
def list_alert_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HotelAlertRuleOut]:
    rows = hotels_service.list_alert_rules(db, current_user.id)
    return [
        HotelAlertRuleOut(
            id=row.id,
            hotel_id=row.hotel_id,
            tracked_offer_id=row.tracked_offer_id,
            compare_against=row.compare_against,
            cooldown_minutes=row.cooldown_minutes,
            evaluation_state=row.evaluation_state,
            last_fired_at=row.last_fired_at,
            rule_type=row.rule_type,
            threshold_amount=float(row.threshold_amount) if row.threshold_amount is not None else None,
            threshold_percent=float(row.threshold_percent) if row.threshold_percent is not None else None,
            is_active=row.is_active,
        )
        for row in rows
    ]


@router.post("/alert-rules", response_model=HotelAlertRuleOut)
def create_alert_rule(
    payload_raw: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelAlertRuleOut:
    try:
        payload = HotelAlertRuleCreateIn.model_validate(payload_raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_extract_validation_error_code(exc)) from exc

    try:
        row = hotels_service.create_alert_rule(
            db,
            user_id=current_user.id,
            hotel_id=payload.hotel_id,
            rule_type=payload.rule_type,
            threshold_amount=payload.threshold_amount,
            threshold_percent=payload.threshold_percent,
            cooldown_minutes=payload.cooldown_minutes,
            is_active=payload.is_active,
            tracked_offer_id=payload.tracked_offer_id,
            compare_against=payload.compare_against,
        )
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return HotelAlertRuleOut(
        id=row.id,
        hotel_id=row.hotel_id,
        tracked_offer_id=row.tracked_offer_id,
        compare_against=row.compare_against,
        rule_type=row.rule_type,
        threshold_amount=float(row.threshold_amount) if row.threshold_amount is not None else None,
        threshold_percent=float(row.threshold_percent) if row.threshold_percent is not None else None,
        is_active=row.is_active,
    )


@router.patch("/alert-rules/{rule_id}", response_model=HotelAlertRuleOut)
def patch_alert_rule(
    rule_id: str,
    payload_raw: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelAlertRuleOut:
    try:
        payload = HotelAlertRuleUpdateIn.model_validate(payload_raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_extract_validation_error_code(exc)) from exc

    try:
        row = hotels_service.update_alert_rule(
            db,
            user_id=current_user.id,
            rule_id=rule_id,
            update_data=payload.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return HotelAlertRuleOut(
        id=row.id,
        hotel_id=row.hotel_id,
        tracked_offer_id=row.tracked_offer_id,
        compare_against=row.compare_against,
        rule_type=row.rule_type,
        threshold_amount=float(row.threshold_amount) if row.threshold_amount is not None else None,
        threshold_percent=float(row.threshold_percent) if row.threshold_percent is not None else None,
        is_active=row.is_active,
    )


@router.delete("/alert-rules/{rule_id}")
def delete_alert_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    try:
        hotels_service.delete_alert_rule(db, user_id=current_user.id, rule_id=rule_id)
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return {"status": "ok"}


@router.get("/alert-events", response_model=list[HotelAlertEventOut])
def list_alert_events(
    hotel_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HotelAlertEventOut]:
    rows = hotels_service.list_hotel_alert_events(
        db,
        user_id=current_user.id,
        hotel_id=hotel_id,
        limit=limit,
        offset=offset,
    )
    return [
        HotelAlertEventOut(
            id=row.id,
            rule_id=row.rule_id,
            hotel_id=row.hotel_id,
            provider_run_id=row.provider_run_id,
            event_type=row.event_type,
            message=row.message,
            trigger_value=float(row.trigger_value) if row.trigger_value is not None else None,
            event_fingerprint=row.event_fingerprint,
            snapshot_before_id=row.snapshot_before_id,
            snapshot_after_id=row.snapshot_after_id,
            baseline_snapshot_id=row.baseline_snapshot_id,
            baseline_source=row.baseline_source,
            baseline_amount=float(row.baseline_amount) if row.baseline_amount is not None else None,
            baseline_currency=row.baseline_currency,
            comparability_key=row.comparability_key,
            reason_code=row.reason_code,
            eligibility_status=row.eligibility_status,
            rule_version=row.rule_version,
            evaluation_state=row.evaluation_state,
            cooldown_until=row.cooldown_until,
            created_at=row.created_at,
        )
        for row in rows
    ]


# ── Tracked Offers ─────────────────────────────────────────────────


@router.get("/area-resolve", response_model=HotelAreaResolveOut)
def area_resolve(
    q: str = Query(min_length=1, max_length=120),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> HotelAreaResolveOut:
    try:
        _ = HotelAreaResolveQueryIn(q=q)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_extract_validation_error_code(exc)) from exc

    try:
        result = hotels_service.area_resolve(db, q=q)
    except ValueError as exc:
        _raise_http_for_value_error(exc)

    return HotelAreaResolveOut(
        area_label=result["area_label"],
        latitude=result["latitude"],
        longitude=result["longitude"],
        country_code=result["country_code"],
        confidence=result["confidence"],
        source=result["source"],
    )


@router.get("/area-search", response_model=list[HotelAreaSearchResultOut])
def area_search(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    radius_km: int = Query(default=5, ge=1, le=50),
    check_in: Date = Query(),
    check_out: Date = Query(),
    guests: int = Query(default=2, ge=1, le=20),
    currency: str = Query(default="EUR", max_length=3),
    min_stars: int | None = Query(default=None, ge=1, le=5),
    max_price: float | None = Query(default=None, ge=0),
    sort: str = Query(default="price", max_length=10),
    use_provider: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HotelAreaSearchResultOut]:
    try:
        query = HotelAreaSearchQueryIn(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            currency=currency,
            min_stars=min_stars,
            max_price=max_price,
            sort=sort,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_extract_validation_error_code(exc)) from exc

    results = hotels_service.area_search(
        db,
        latitude=query.latitude,
        longitude=query.longitude,
        radius_km=query.radius_km,
        check_in=query.check_in,
        check_out=query.check_out,
        guests=query.guests,
        currency=query.currency,
        min_stars=query.min_stars,
        max_price=query.max_price,
        sort=query.sort,
        user_id=current_user.id,
        use_provider=use_provider,
    )
    return [
        HotelAreaSearchResultOut(
            hotel_id=r["hotel_id"],
            canonical_name=r["canonical_name"],
            city=r["city"],
            country_code=r["country_code"],
            stars=r["stars"],
            distance_km=r["distance_km"],
            lowest_price=r["lowest_price"],
            currency=r["currency"],
            provider=r["provider"],
            check_in=r["check_in"],
            check_out=r["check_out"],
            guests=r["guests"],
            has_tracking=r["has_tracking"],
        )
        for r in results
    ]


@router.get("/v2/area-search", response_model=HotelV2AreaSearchOut)
def area_search_v2(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    radius_km: int = Query(default=5, ge=1, le=50),
    check_in: Date = Query(),
    check_out: Date = Query(),
    guests: int = Query(default=2, ge=1, le=20),
    currency: str = Query(default="EUR", max_length=3),
    min_stars: int | None = Query(default=None, ge=1, le=5),
    max_price: float | None = Query(default=None, ge=0),
    sort: str = Query(default="price", max_length=10),
    use_provider: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelV2AreaSearchOut:
    try:
        query = HotelAreaSearchQueryIn(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            currency=currency,
            min_stars=min_stars,
            max_price=max_price,
            sort=sort,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_extract_validation_error_code(exc)) from exc

    provider_state: dict[str, str] = {}
    results = hotels_service.area_search(
        db,
        latitude=query.latitude,
        longitude=query.longitude,
        radius_km=query.radius_km,
        check_in=query.check_in,
        check_out=query.check_out,
        guests=query.guests,
        currency=query.currency,
        min_stars=query.min_stars,
        max_price=query.max_price,
        sort=query.sort,
        user_id=current_user.id,
        use_provider=use_provider,
        provider_state=provider_state,
    )
    warnings: list[HotelV2WarningOut] = []
    providers: list[HotelV2ProviderOut] = []
    if use_provider:
        activation = resolve_hotel_activation(operation="area_search")
        if not activation.external_calls_allowed:
            providers.append(
                HotelV2ProviderOut(
                    id=activation.provider,
                    operation="area_search",
                    status="disabled",
                )
            )
            warnings.append(
                HotelV2WarningOut(
                    code="provider_unavailable",
                    severity="warning",
                    message_key="hotels.warnings.providerUnavailable",
                    provider=activation.provider,
                    meta={"reason": activation.reason},
                )
            )
        elif provider_state:
            provider = provider_state["provider"]
            providers.append(
                HotelV2ProviderOut(
                    id=provider,
                    operation="area_search",
                    status=provider_state["status"],
                    fallback_used=bool(results),
                )
            )
            warnings.append(
                HotelV2WarningOut(
                    code="provider_unavailable",
                    severity="warning",
                    message_key="hotels.warnings.providerUnavailable",
                    provider=provider,
                    meta={"reason": "provider_fetch_failed"},
                )
            )

    data = [
        HotelV2AreaSearchResultOut(
            hotel_id=result["hotel_id"],
            canonical_name=result["canonical_name"],
            city=result["city"],
            country_code=result["country_code"],
            stars=result["stars"],
            distance_km=result["distance_km"],
            price=HotelV2PriceOut(
                amount=(
                    result["amount_total"]
                    if result["price_semantics"] == "total" and result["amount_total"] is not None
                    else result["lowest_price"]
                ),
                currency=result["currency"],
                basis=(
                    "total_stay"
                    if result["price_semantics"] == "total" and result["amount_total"] is not None
                    else "unknown"
                ),
                status="observed" if result["lowest_price"] is not None else "unavailable",
                observed_at=result["observed_at"],
            ),
            stay_context=HotelV2StayContextOut(
                check_in=result["check_in"],
                check_out=result["check_out"],
                guests=result["guests"],
            ),
            provider=result["provider"],
            has_tracking=result["has_tracking"],
            explanation=HotelV2ResultExplanationOut(
                primary_reason="lowest_observed_price" if result["lowest_price"] is not None else "price_unavailable",
                codes=["price_context_match"] if result["lowest_price"] is not None else ["price_unavailable"],
            ),
        )
        for result in results
    ]
    result_state = "partial" if warnings else "success" if data else "empty"
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return HotelV2AreaSearchOut(
        data=data,
        meta=HotelV2ResultsMetaOut(
            request_id=get_correlation_id() or str(uuid4()),
            generated_at=generated_at,
            result_state=result_state,
            query={
                "mode": "area",
                "check_in": query.check_in.isoformat(),
                "check_out": query.check_out.isoformat(),
                "guests": query.guests,
                "currency": query.currency,
                "radius_km": query.radius_km,
                "filters": {"min_stars": query.min_stars, "max_price": query.max_price},
                "sort": query.sort,
            },
            pagination=HotelV2PaginationOut(returned=len(data), total=len(data), sort=query.sort),
            freshness=HotelV2FreshnessOut(),
            providers=providers,
            capabilities={
                "filters": {
                    "radius_km": "supported",
                    "min_stars": "supported",
                    "max_price": "supported_with_caveat",
                    "cancellation": "unavailable",
                    "rooms": "planned",
                },
                "sorts": {
                    "price": "supported",
                    "distance": "supported",
                    "stars": "supported",
                    "recommended": "unavailable",
                },
                "actions": {
                    "track": "supported",
                    "deeplink": "unavailable",
                    "refresh": "planned",
                },
            },
            warnings=warnings,
        ),
    )


@router.get("/tracked-offers", response_model=list[HotelTrackedOfferOut])
def list_tracked_offers(
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HotelTrackedOfferOut]:
    rows = hotels_service.list_tracked_offers(db, user_id=current_user.id, is_active=is_active)
    return [
        HotelTrackedOfferOut(
            id=row.id,
            user_id=row.user_id,
            hotel_id=row.hotel_id,
            area_label=row.area_label,
            origin_query=row.origin_query,
            latitude=float(row.latitude) if row.latitude is not None else None,
            longitude=float(row.longitude) if row.longitude is not None else None,
            radius_km=row.radius_km,
            check_in=row.check_in,
            check_out=row.check_out,
            guests=row.guests,
            room_label=row.room_label,
            meal_plan=row.meal_plan,
            cancellation_policy=row.cancellation_policy,
            provider=row.provider,
            initial_price=float(row.initial_price) if row.initial_price is not None else None,
            current_price=float(row.current_price) if row.current_price is not None else None,
            target_price=float(row.target_price) if row.target_price is not None else None,
            currency=row.currency,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.get("/v2/tracked-offers", response_model=HotelV2TrackedOffersOut)
def list_tracked_offers_v2(
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelV2TrackedOffersOut:
    projections = hotels_service.list_tracked_offer_statuses(
        db,
        user_id=current_user.id,
        is_active=is_active,
    )
    data = [_tracked_offer_v2_out(projection) for projection in projections]
    result_state = "empty" if not data else "partial" if any(item.warnings for item in data) else "success"
    return HotelV2TrackedOffersOut(
        data=data,
        meta=HotelV2TrackedOffersMetaOut(
            request_id=get_correlation_id() or str(uuid4()),
            generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            result_state=result_state,
            query={"is_active": is_active},
            pagination=HotelV2PaginationOut(returned=len(data), total=len(data), sort="created_at"),
            freshness=HotelV2FreshnessOut(),
            capabilities={
                "read": "supported",
                "v1_fallback": "supported_with_caveat",
                "cursor_pagination": "planned",
            },
        ),
    )


def _tracked_offer_v2_out(projection: hotels_service.HotelTrackedOfferStatus) -> HotelV2TrackedOfferOut:
    offer = projection.offer
    snapshot = projection.latest_snapshot
    warnings = [
        HotelV2WarningOut(
            code=code,
            severity="warning",
            message_key=f"hotels.tracking.warnings.{code}",
            scope="result",
            result_ids=[offer.id],
        )
        for code in projection.warning_codes
    ]
    latest_observation = None
    if snapshot is not None:
        is_total_stay = snapshot.price_semantics == "total" and snapshot.amount_total is not None
        price_status = (
            "observed"
            if snapshot.snapshot_outcome == "success" and snapshot.availability_status in {"available", "limited"}
            else "stale"
            if snapshot.availability_status == "stale"
            else "unavailable"
            if snapshot.availability_status not in {"available", "limited"}
            else "not_comparable"
        )
        latest_observation = HotelV2TrackingObservationOut(
            snapshot_id=snapshot.id,
            legacy_collected_at=snapshot.collected_at,
            observed_at=snapshot.observed_at,
            provider=snapshot.provider,
            room_label=snapshot.room_label,
            meal_plan=snapshot.meal_plan,
            cancellation_policy=snapshot.cancellation_policy,
            availability_status=snapshot.availability_status,
            conditions_completeness=snapshot.conditions_completeness,
            canonical_stay_offer_id=snapshot.stay_offer_id,
            price=HotelV2PriceOut(
                amount=float(snapshot.amount_total if is_total_stay else snapshot.amount),
                currency=snapshot.currency,
                basis="total_stay" if is_total_stay else "unknown",
                status=price_status,
                observed_at=snapshot.observed_at,
            ),
            freshness=_hotel_v2_freshness_out(snapshot),
        )
    return HotelV2TrackedOfferOut(
        id=offer.id,
        hotel_id=offer.hotel_id,
        state_version=offer.lifecycle_version or 1,
        state=projection.state,
        stay_context=HotelV2TrackingStayContextOut(
            check_in=offer.check_in,
            check_out=offer.check_out,
            guests=offer.guests,
            currency=offer.currency,
        ),
        latest_observation=latest_observation,
        capabilities={
            "pause": "supported" if projection.state != "archived" else "unavailable",
            "resume": "supported" if projection.state == "paused" else "unavailable",
            "archive": "supported" if projection.state != "archived" else "unavailable",
            "edit_target": "supported",
            "delete": "supported",
            "create_alert": "supported_with_caveat",
            "external_delivery": "unavailable",
        },
        warnings=warnings,
    )


def _hotel_v2_freshness_out(snapshot: HotelRateSnapshot | None) -> HotelV2FreshnessOut:
    freshness = hotels_service.classify_hotel_observation_freshness(
        hotels_service.HotelObservationFreshnessInput(
        observed_at=snapshot.observed_at if snapshot is not None else None,
        collected_at=snapshot.collected_at if snapshot is not None else None,
        provider=snapshot.provider if snapshot is not None else None,
        )
    )
    return HotelV2FreshnessOut(
        state=freshness.state,
        observed_at=freshness.observed_at,
        age_seconds=freshness.age_seconds,
        expires_at=freshness.expires_at,
        requires_revalidation=freshness.requires_revalidation,
        policy_version="hotel-freshness-v1",
        provenance_kind=freshness.provenance_kind,
    )


def _tracked_offer_history_v2_out(
    offer: HotelTrackedOffer,
    snapshots: list[HotelRateSnapshot],
) -> HotelV2TrackedOfferHistoryOut:
    fingerprints = {snapshot.offer_fingerprint for snapshot in snapshots}
    stay_offer_ids = {snapshot.stay_offer_id for snapshot in snapshots}
    currencies = {snapshot.currency for snapshot in snapshots}
    providers = {snapshot.provider for snapshot in snapshots}
    canonical_identity = (
        bool(snapshots)
        and None not in fingerprints
        and None not in stay_offer_ids
        and len(fingerprints) == 1
        and len(stay_offer_ids) == 1
        and len(currencies) == 1
    )
    identity_status = "comparable" if canonical_identity else "legacy_comparison" if len(currencies) == 1 else "not_comparable"
    point_inputs: list[tuple[HotelRateSnapshot, str | None]] = []
    for snapshot in snapshots:
        excluded_reason = None
        if identity_status != "comparable":
            excluded_reason = "history_identity_not_comparable"
        elif snapshot.snapshot_outcome != "success":
            excluded_reason = "snapshot_not_success"
        elif snapshot.availability_status not in {"available", "limited"}:
            excluded_reason = f"availability_{snapshot.availability_status}"
        elif snapshot.price_semantics != "total" or snapshot.amount_total is None:
            excluded_reason = "total_price_missing"
        elif snapshot.conditions_completeness != "complete":
            excluded_reason = "conditions_incomplete"
        point_inputs.append((snapshot, excluded_reason))

    exclusions: dict[str, int] = {}
    eligible_amounts: list[float] = []
    points: list[HotelV2HistoryPointOut] = []
    for snapshot, excluded_reason in point_inputs:
        is_total_stay = snapshot.price_semantics == "total" and snapshot.amount_total is not None
        price_status = (
            "observed"
            if snapshot.snapshot_outcome == "success" and snapshot.availability_status in {"available", "limited"}
            else "stale"
            if snapshot.availability_status == "stale"
            else "unavailable"
            if snapshot.availability_status not in {"available", "limited"}
            else "not_comparable"
        )
        if excluded_reason is None:
            eligible_amounts.append(float(snapshot.amount_total))
        else:
            exclusions[excluded_reason] = exclusions.get(excluded_reason, 0) + 1
        points.append(
            HotelV2HistoryPointOut(
                snapshot_id=snapshot.id,
                observed_at=snapshot.observed_at or snapshot.collected_at,
                observation_time_source="provider_observed" if snapshot.observed_at is not None else "legacy_collected",
                provider=snapshot.provider,
                availability_status=snapshot.availability_status,
                conditions_completeness=snapshot.conditions_completeness,
                canonical_stay_offer_id=snapshot.stay_offer_id,
                price_semantics="total" if is_total_stay else "unknown",
                price=HotelV2PriceOut(
                    amount=float(snapshot.amount_total if is_total_stay else snapshot.amount),
                    currency=snapshot.currency,
                    basis="total_stay" if is_total_stay else "unknown",
                    status=price_status,
                    observed_at=snapshot.observed_at,
                ),
                eligibility="eligible" if excluded_reason is None else "excluded",
                excluded_reason=excluded_reason,
            )
        )

    ordered_amounts = sorted(eligible_amounts)
    midpoint = len(ordered_amounts) // 2
    median = None
    average = None
    if len(ordered_amounts) >= 3:
        median = (
            ordered_amounts[midpoint]
            if len(ordered_amounts) % 2
            else (ordered_amounts[midpoint - 1] + ordered_amounts[midpoint]) / 2
        )
        average = sum(ordered_amounts) / len(ordered_amounts)
    return HotelV2TrackedOfferHistoryOut(
        tracked_offer_id=offer.id,
        series=HotelV2HistorySeriesOut(
            identity=HotelV2HistoryIdentityOut(
                comparability_key=next(iter(fingerprints)) if canonical_identity else None,
                status=identity_status,
                check_in=offer.check_in,
                check_out=offer.check_out,
                guests=offer.guests,
                currency=offer.currency,
                provider_scope=next(iter(providers)) if len(providers) == 1 else None,
            ),
            points=points,
        ),
        aggregates=HotelV2HistoryAggregatesOut(
            sample_size_total=len(points),
            sample_size_eligible=len(eligible_amounts),
            min_price=min(eligible_amounts) if eligible_amounts else None,
            max_price=max(eligible_amounts) if eligible_amounts else None,
            median_price=median,
            average_price=average,
            currency=offer.currency,
            price_semantics="total" if canonical_identity else "unknown",
            exclusions=exclusions,
        ),
        freshness=_hotel_v2_freshness_out(snapshots[-1] if snapshots else None),
        capabilities={
            "raw_series": "supported",
            "window": "supported",
            "gap_detection": "unavailable",
            "trend_comparisons": "unavailable",
        },
    )


@router.get("/v2/tracked-offers/{tracked_offer_id}/history", response_model=HotelV2TrackedOfferHistoryOut)
def get_tracked_offer_history_v2(
    tracked_offer_id: str,
    from_date: Date | None = Query(default=None, alias="from"),
    to_date: Date | None = Query(default=None, alias="to"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelV2TrackedOfferHistoryOut:
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="hotel_history_invalid_window")
    try:
        offer, snapshots = hotels_service.list_tracked_offer_history_snapshots(
            db,
            user_id=current_user.id,
            tracked_offer_id=tracked_offer_id,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
        )
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return _tracked_offer_history_v2_out(offer, snapshots)


@router.post("/v2/tracked-offers", response_model=HotelV2TrackedOfferCreateOut, status_code=201)
def create_tracked_offer_v2(
    payload: HotelV2TrackedOfferCreateIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelV2TrackedOfferCreateOut:
    try:
        creation = hotels_service.create_tracked_offer_from_v2_source_rate(
            db,
            user_id=current_user.id,
            source_rate_id=payload.source_rate_id,
        )
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    if not creation.created:
        response.status_code = 200
    projection = next(
        item
        for item in hotels_service.list_tracked_offer_statuses(db, user_id=current_user.id)
        if item.offer.id == creation.offer.id
    )
    return HotelV2TrackedOfferCreateOut(
        tracking=_tracked_offer_v2_out(projection),
        creation=HotelV2TrackedOfferCreationMetaOut(
            outcome="created" if creation.created else "existing",
            semantic_dedupe=not creation.created,
        ),
    )


@router.patch(
    "/v2/tracked-offers/{tracked_offer_id}/lifecycle",
    response_model=HotelV2TrackedOfferLifecycleOut,
)
def transition_tracked_offer_v2_lifecycle(
    tracked_offer_id: str,
    payload: HotelV2TrackedOfferLifecycleIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelV2TrackedOfferLifecycleOut:
    try:
        transition = hotels_service.transition_tracked_offer_lifecycle(
            db,
            user_id=current_user.id,
            tracked_offer_id=tracked_offer_id,
            action=payload.action,
            expected_state_version=payload.expected_state_version,
        )
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    projection = next(
        item
        for item in hotels_service.list_tracked_offer_statuses(db, user_id=current_user.id)
        if item.offer.id == transition.offer.id
    )
    return HotelV2TrackedOfferLifecycleOut(
        tracking=_tracked_offer_v2_out(projection),
        outcome=transition.outcome,
    )


@router.post("/tracked-offers", response_model=HotelTrackedOfferOut, status_code=201)
def create_tracked_offer(
    payload: HotelTrackedOfferCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelTrackedOfferOut:
    try:
        row = hotels_service.create_tracked_offer(
            db,
            user_id=current_user.id,
            hotel_id=payload.hotel_id,
            area_label=payload.area_label,
            origin_query=payload.origin_query,
            latitude=payload.latitude,
            longitude=payload.longitude,
            radius_km=payload.radius_km,
            check_in=payload.check_in,
            check_out=payload.check_out,
            guests=payload.guests,
            room_label=payload.room_label,
            meal_plan=payload.meal_plan,
            cancellation_policy=payload.cancellation_policy,
            provider=payload.provider,
            initial_price=payload.initial_price,
            current_price=payload.current_price,
            target_price=payload.target_price,
            currency=payload.currency,
        )
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    return HotelTrackedOfferOut(
        id=row.id,
        user_id=row.user_id,
        hotel_id=row.hotel_id,
        area_label=row.area_label,
        origin_query=row.origin_query,
        latitude=float(row.latitude) if row.latitude is not None else None,
        longitude=float(row.longitude) if row.longitude is not None else None,
        radius_km=row.radius_km,
        check_in=row.check_in,
        check_out=row.check_out,
        guests=row.guests,
        room_label=row.room_label,
        meal_plan=row.meal_plan,
        cancellation_policy=row.cancellation_policy,
        provider=row.provider,
        initial_price=float(row.initial_price) if row.initial_price is not None else None,
        current_price=float(row.current_price) if row.current_price is not None else None,
        target_price=float(row.target_price) if row.target_price is not None else None,
        currency=row.currency,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/tracked-offers/{tracked_offer_id}", response_model=HotelTrackedOfferOut)
def get_tracked_offer(
    tracked_offer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelTrackedOfferOut:
    try:
        row = hotels_service.get_tracked_offer_or_404(db, user_id=current_user.id, tracked_offer_id=tracked_offer_id)
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return HotelTrackedOfferOut(
        id=row.id,
        user_id=row.user_id,
        hotel_id=row.hotel_id,
        area_label=row.area_label,
        origin_query=row.origin_query,
        latitude=float(row.latitude) if row.latitude is not None else None,
        longitude=float(row.longitude) if row.longitude is not None else None,
        radius_km=row.radius_km,
        check_in=row.check_in,
        check_out=row.check_out,
        guests=row.guests,
        room_label=row.room_label,
        meal_plan=row.meal_plan,
        cancellation_policy=row.cancellation_policy,
        provider=row.provider,
        initial_price=float(row.initial_price) if row.initial_price is not None else None,
        current_price=float(row.current_price) if row.current_price is not None else None,
        target_price=float(row.target_price) if row.target_price is not None else None,
        currency=row.currency,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.patch("/tracked-offers/{tracked_offer_id}", response_model=HotelTrackedOfferOut)
def update_tracked_offer(
    tracked_offer_id: str,
    payload_raw: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HotelTrackedOfferOut:
    try:
        payload = HotelTrackedOfferUpdateIn.model_validate(payload_raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_extract_validation_error_code(exc)) from exc

    try:
        row = hotels_service.update_tracked_offer(
            db,
            user_id=current_user.id,
            tracked_offer_id=tracked_offer_id,
            update_data=payload.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return HotelTrackedOfferOut(
        id=row.id,
        user_id=row.user_id,
        hotel_id=row.hotel_id,
        area_label=row.area_label,
        origin_query=row.origin_query,
        latitude=float(row.latitude) if row.latitude is not None else None,
        longitude=float(row.longitude) if row.longitude is not None else None,
        radius_km=row.radius_km,
        check_in=row.check_in,
        check_out=row.check_out,
        guests=row.guests,
        room_label=row.room_label,
        meal_plan=row.meal_plan,
        cancellation_policy=row.cancellation_policy,
        provider=row.provider,
        initial_price=float(row.initial_price) if row.initial_price is not None else None,
        current_price=float(row.current_price) if row.current_price is not None else None,
        target_price=float(row.target_price) if row.target_price is not None else None,
        currency=row.currency,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.delete("/tracked-offers/{tracked_offer_id}")
def delete_tracked_offer(
    tracked_offer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    try:
        hotels_service.delete_tracked_offer(db, user_id=current_user.id, tracked_offer_id=tracked_offer_id)
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return {"status": "ok"}


@router.get("/tracked-offers/{tracked_offer_id}/snapshots", response_model=list[HotelRateOut])
def get_tracked_offer_snapshots(
    tracked_offer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HotelRateOut]:
    try:
        rows = hotels_service.list_tracked_offer_snapshots(db, user_id=current_user.id, tracked_offer_id=tracked_offer_id)
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return [
        HotelRateOut(
            id=row.id,
            hotel_id=row.hotel_id,
            tracked_offer_id=row.tracked_offer_id,
            provider_run_id=row.provider_run_id,
            provider=row.provider,
            check_in=row.check_in,
            check_out=row.check_out,
            guests=row.guests,
            room_label=row.room_label,
            meal_plan=row.meal_plan,
            cancellation_policy=row.cancellation_policy,
            currency=row.currency,
            amount=float(row.amount),
            availability_status=row.availability_status,
            deep_link=sanitize_hotel_deep_link(row.deep_link, provider=row.provider),
            collected_at=row.collected_at,
        )
        for row in rows
    ]


@router.get("/{hotel_id}", response_model=HotelDetailOut)
def get_hotel_detail(
    hotel_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> HotelDetailOut:
    try:
        hotel = hotels_service.get_hotel_or_404(db, hotel_id)
    except ValueError as exc:
        _raise_http_for_value_error(exc)

    return HotelDetailOut(
        id=hotel.id,
        canonical_name=hotel.canonical_name,
        normalized_name=hotel.normalized_name,
        address=hotel.address,
        city=hotel.city,
        country_code=hotel.country_code,
        latitude=float(hotel.latitude) if hotel.latitude is not None else None,
        longitude=float(hotel.longitude) if hotel.longitude is not None else None,
        stars=hotel.stars,
        created_at=hotel.created_at,
        updated_at=hotel.updated_at,
    )


@router.get("/{hotel_id}/rates", response_model=list[HotelRateOut])
def get_hotel_rates(
    hotel_id: str,
    check_in: Date | None = None,
    check_out: Date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[HotelRateOut]:
    try:
        _ = hotels_service.get_hotel_or_404(db, hotel_id)
    except ValueError as exc:
        _raise_http_for_value_error(exc)

    try:
        query = HotelRatesQueryIn(check_in=check_in, check_out=check_out)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_extract_validation_error_code(exc)) from exc

    rows = hotels_service.list_hotel_rates(db, hotel_id=hotel_id, check_in=query.check_in, check_out=query.check_out)
    return [
        HotelRateOut(
            id=row.id,
            hotel_id=row.hotel_id,
            tracked_offer_id=row.tracked_offer_id,
            provider_run_id=row.provider_run_id,
            provider=row.provider,
            check_in=row.check_in,
            check_out=row.check_out,
            guests=row.guests,
            room_label=row.room_label,
            meal_plan=row.meal_plan,
            cancellation_policy=row.cancellation_policy,
            currency=row.currency,
            amount=float(row.amount),
            availability_status=row.availability_status,
            deep_link=sanitize_hotel_deep_link(row.deep_link, provider=row.provider),
            collected_at=row.collected_at,
        )
        for row in rows
    ]


@router.get("/{hotel_id}/parity", response_model=list[HotelParityOut])
def get_hotel_parity(
    hotel_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[HotelParityOut]:
    try:
        signals = hotels_service.get_hotel_parity(db, hotel_id=hotel_id)
    except ValueError as exc:
        _raise_http_for_value_error(exc)

    return [
        HotelParityOut(
            check_in=s.check_in,
            check_out=s.check_out,
            guests=s.guests,
            currency=s.currency,
            provider_count=s.provider_count,
            lowest_price=s.lowest_price,
            highest_price=s.highest_price,
            average_price=s.average_price,
            spread_amount=s.spread_amount,
            spread_percent=s.spread_percent,
            is_parity_broken=s.is_parity_broken,
            status=s.status,
            label=s.label,
        )
        for s in signals
    ]
