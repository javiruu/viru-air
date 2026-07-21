from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.live_flight_schemas import LiveFlightTrackingOut
from app.infrastructure.db.models import FlightWatch, User
from app.infrastructure.db.session import get_db
from app.infrastructure.providers.aviationstack_operational_provider import build_operational_provider
from app.services.live_flight_tracking import build_live_tracking_response, refresh_live_tracking


router = APIRouter()


@router.get("/{watch_id}/live", response_model=LiveFlightTrackingOut)
def get_watch_live_tracking(
    watch_id: str,
    refresh: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LiveFlightTrackingOut:
    watch = db.scalar(
        select(FlightWatch).where(
            FlightWatch.id == watch_id,
            FlightWatch.user_id == current_user.id,
            FlightWatch.status != "deleted",
        )
    )
    if watch is None:
        raise HTTPException(status_code=404, detail="watch_not_found")
    provider_status = refresh_live_tracking(db, watch, build_operational_provider(), refresh)
    return build_live_tracking_response(db, watch, provider_status)
