from datetime import date as Date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import (
    HotelAlertEventOut,
    HotelAlertRuleCreateIn,
    HotelAlertRuleOut,
    HotelAlertRuleUpdateIn,
    HotelCompSetCreateIn,
    HotelCompSetDetailOut,
    HotelCompSetMemberCreateIn,
    HotelCompSetMemberOut,
    HotelCompSetOut,
    HotelDetailOut,
    HotelIngestOut,
    HotelParityOut,
    HotelProviderRunOut,
    HotelRateOut,
    HotelRatesQueryIn,
    HotelSearchOut,
    HotelSearchQueryIn,
    HotelWatchlistItemCreateIn,
    HotelWatchlistItemOut,
)
from app.infrastructure.db.models import User
from app.infrastructure.db.session import get_db
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
        "hotel_watchlist_item_not_found",
        "hotel_comp_set_not_found",
        "hotel_comp_set_member_not_found",
        "hotel_alert_rule_not_found",
    }:
        raise HTTPException(status_code=404, detail=code) from exc
    if code in {
        "hotel_watchlist_item_already_exists",
        "hotel_comp_set_member_already_exists",
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
    result = hotels_service.ingest_hotels_mock(db)
    return HotelIngestOut(
        provider_id=result.provider_id,
        hotels_processed=result.hotels_processed,
        rates_ingested=result.rates_ingested,
        ambiguous_matches=result.ambiguous_matches,
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
            is_active=payload.is_active,
        )
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    return HotelAlertRuleOut(
        id=row.id,
        hotel_id=row.hotel_id,
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
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HotelAlertEventOut]:
    rows = hotels_service.list_hotel_alert_events(db, user_id=current_user.id, limit=limit, offset=offset)
    return [
        HotelAlertEventOut(
            id=row.id,
            rule_id=row.rule_id,
            hotel_id=row.hotel_id,
            provider_run_id=row.provider_run_id,
            event_type=row.event_type,
            message=row.message,
            trigger_value=float(row.trigger_value) if row.trigger_value is not None else None,
            created_at=row.created_at,
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
            provider=row.provider,
            check_in=row.check_in,
            check_out=row.check_out,
            guests=row.guests,
            room_label=row.room_label,
            meal_plan=row.meal_plan,
            cancellation_policy=row.cancellation_policy,
            currency=row.currency,
            amount=float(row.amount),
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
