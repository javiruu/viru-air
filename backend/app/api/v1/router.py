from fastapi import APIRouter

from app.door_to_door.api import routes as door_to_door

from app.api.v1 import (
    account,
    admin,
    alerts,
    airports,
    auth,
    notes,
    preferences,
    prices,
    public,
    recommendations,
    search,
    suggestions,
    support,
    ux,
    watchlist,
)

api_v1 = APIRouter()
api_v1.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1.include_router(admin.router, prefix="/admin", tags=["admin"])
api_v1.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
api_v1.include_router(door_to_door.router, prefix="/door-to-door", tags=["door-to-door"])
api_v1.include_router(prices.router, prefix="/prices", tags=["prices"])
api_v1.include_router(search.router, prefix="/search", tags=["search"])
api_v1.include_router(airports.router, prefix="/airports", tags=["airports"])
api_v1.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_v1.include_router(preferences.router, prefix="/preferences", tags=["preferences"])
api_v1.include_router(suggestions.router, prefix="/suggestions", tags=["suggestions"])
api_v1.include_router(notes.router, prefix="/notes", tags=["notes"])
api_v1.include_router(account.router, prefix="/account", tags=["account"])
api_v1.include_router(support.router, prefix="/support", tags=["support"])
api_v1.include_router(public.router, prefix="/public", tags=["public"])
api_v1.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_v1.include_router(ux.router, prefix="/ux", tags=["ux"])
