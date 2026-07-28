from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import (
    CommunityPriceDeleteOut,
    CommunityPriceMutationOut,
    CommunityPriceReportIn,
)
from app.domain.vocabulary import (
    WATCH_STATUS_DELETED,
    WATCH_STATUS_PURCHASED,
)
from app.infrastructure.db.models import CommunityPriceReport, FlightWatch, User
from app.infrastructure.db.session import get_db
from app.services.community_pricing import (
    community_pricing_for_watch,
    community_trigger_reason,
)

router = APIRouter()


def _owned_watch(db: Session, watch_id: str, user_id: str) -> FlightWatch:
    watch = db.scalar(
        select(FlightWatch).where(
            FlightWatch.id == watch_id,
            FlightWatch.user_id == user_id,
        )
    )
    if watch is None or watch.status == WATCH_STATUS_DELETED:
        raise HTTPException(status_code=404, detail="watch_not_found")
    return watch


def _mutation_out(
    db: Session,
    watch: FlightWatch,
    *,
    current_user_id: str,
) -> CommunityPriceMutationOut:
    return CommunityPriceMutationOut(
        watch_id=watch.id,
        status=watch.status,
        community_pricing=community_pricing_for_watch(
            db,
            watch,
            current_user_id=current_user_id,
        ),
    )


@router.post("/{watch_id}/mark-purchased", response_model=CommunityPriceMutationOut)
def mark_watch_purchased(
    watch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommunityPriceMutationOut:
    watch = _owned_watch(db, watch_id, current_user.id)
    watch.status = WATCH_STATUS_PURCHASED
    db.commit()
    db.refresh(watch)
    return _mutation_out(db, watch, current_user_id=current_user.id)


@router.put("/{watch_id}/community-price", response_model=CommunityPriceMutationOut)
def upsert_community_price(
    watch_id: str,
    payload: CommunityPriceReportIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommunityPriceMutationOut:
    watch = _owned_watch(db, watch_id, current_user.id)
    trigger_reason = community_trigger_reason(watch)
    if trigger_reason is None:
        raise HTTPException(status_code=409, detail="community_price_not_eligible")

    report = db.scalar(
        select(CommunityPriceReport).where(
            CommunityPriceReport.watch_id == watch.id,
            CommunityPriceReport.user_id == current_user.id,
        )
    )
    price = (
        float(payload.price_per_traveler)
        if payload.price_per_traveler is not None
        else None
    )
    if report is None:
        report = CommunityPriceReport(
            watch_id=watch.id,
            user_id=current_user.id,
            trigger_reason=trigger_reason,
            flew=payload.flew,
            price_per_traveler=price,
            currency=payload.currency,
        )
        db.add(report)
    else:
        report.trigger_reason = trigger_reason
        report.flew = payload.flew
        report.price_per_traveler = price
        report.currency = payload.currency
    db.commit()
    return _mutation_out(db, watch, current_user_id=current_user.id)


@router.delete(
    "/{watch_id}/community-price",
    response_model=CommunityPriceDeleteOut,
)
def delete_community_price(
    watch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommunityPriceDeleteOut:
    watch = _owned_watch(db, watch_id, current_user.id)
    report = db.scalar(
        select(CommunityPriceReport).where(
            CommunityPriceReport.watch_id == watch.id,
            CommunityPriceReport.user_id == current_user.id,
        )
    )
    if report is None:
        raise HTTPException(status_code=404, detail="community_price_not_found")
    db.delete(report)
    db.commit()
    return CommunityPriceDeleteOut()
