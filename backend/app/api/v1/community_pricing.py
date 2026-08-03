from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import (
    CommunityContributorStatsOut,
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


@router.get("/contributor-stats", response_model=CommunityContributorStatsOut)
def get_contributor_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommunityContributorStatsOut:
    """Return the authenticated user's total community contributions and weekly streak."""
    from datetime import date, timedelta

    rows = list(
        db.execute(
            select(CommunityPriceReport.created_at)
            .where(
                CommunityPriceReport.user_id == current_user.id,
                CommunityPriceReport.flew.is_(True),
                CommunityPriceReport.price_per_traveler.is_not(None),
            )
            .order_by(CommunityPriceReport.created_at.desc())
        ).scalars().all()
    )

    total = len(rows)
    if total == 0:
        return CommunityContributorStatsOut(total_contributions=0, streak_weeks=0)

    # Calculate consecutive-week streak (ISO weeks, going backwards from today)
    today = date.today()
    current_monday = today - timedelta(days=today.weekday())
    reported_weeks: set[str] = set()
    for created_at in rows:
        d = created_at.date() if hasattr(created_at, "date") else created_at
        monday = d - timedelta(days=d.weekday())
        reported_weeks.add(monday.isoformat())

    streak = 0
    check_monday = current_monday
    for _ in range(52):  # cap at 52 weeks
        if check_monday.isoformat() in reported_weeks:
            streak += 1
            check_monday -= timedelta(days=7)
        else:
            # Allow skipping the current week (it might not be over yet)
            if streak == 0 and check_monday == current_monday:
                check_monday -= timedelta(days=7)
                continue
            break

    return CommunityContributorStatsOut(
        total_contributions=total,
        streak_weeks=streak,
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
