from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import (
    CommunityPopularRoutesOut,
    CommunityRelatedRoutesOut,
    CommunityRouteIn,
    CommunityRouteInsightsIn,
    CommunityRouteInsightsOut,
)
from app.infrastructure.db.models import User
from app.infrastructure.db.session import get_db
from app.services.community_route_intelligence import (
    list_popular_routes,
    list_related_routes,
    build_route_insights,
)

router = APIRouter()


@router.get("/popular", response_model=CommunityPopularRoutesOut)
def popular_routes(
    limit: int = Query(default=10, ge=1, le=10),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> CommunityPopularRoutesOut:
    return CommunityPopularRoutesOut(routes=list_popular_routes(db, limit=limit))


@router.post("/insights", response_model=CommunityRouteInsightsOut)
def route_insights(
    payload: CommunityRouteInsightsIn,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> CommunityRouteInsightsOut:
    return CommunityRouteInsightsOut(routes=build_route_insights(db, payload.routes))


@router.get(
    "/{origin_iata}/{destination_iata}/related",
    response_model=CommunityRelatedRoutesOut,
)
def related_routes(
    origin_iata: str,
    destination_iata: str,
    limit: int = Query(default=3, ge=1, le=3),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> CommunityRelatedRoutesOut:
    route = CommunityRouteIn(
        origin_iata=origin_iata,
        destination_iata=destination_iata,
    )
    return CommunityRelatedRoutesOut(
        routes=list_related_routes(
            db,
            route.origin_iata,
            route.destination_iata,
            limit=limit,
        )
    )
