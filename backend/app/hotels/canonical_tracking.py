from __future__ import annotations

import json

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.hotels.stay_offer import CancellationPolicy, OfferIdentity, RoomSignature, stay_query_from_legacy
from app.infrastructure.db.models import HotelProviderAlias, HotelStayOffer, HotelTrackedOffer, HotelUserStayWatch


def write_canonical_tracking_watch(db: Session, *, tracked_offer: HotelTrackedOffer) -> HotelStayOffer | None:
    if tracked_offer.check_in is None or tracked_offer.check_out is None:
        return None
    if any(
        value is not None
        for value in (
            tracked_offer.room_label,
            tracked_offer.meal_plan,
            tracked_offer.cancellation_policy,
        )
    ):
        return None

    provider_alias = db.scalar(
        select(HotelProviderAlias).where(
            HotelProviderAlias.hotel_id == tracked_offer.hotel_id,
            HotelProviderAlias.provider == tracked_offer.provider,
            or_(
                HotelProviderAlias.confidence_score.is_(None),
                HotelProviderAlias.confidence_score > 0,
            ),
        )
    )
    if provider_alias is None:
        raise ValueError("canonical_tracking_alias_missing")

    stay_query = stay_query_from_legacy(
        canonical_hotel_id=tracked_offer.hotel_id,
        area_key=None,
        check_in=tracked_offer.check_in,
        check_out=tracked_offer.check_out,
        guests=tracked_offer.guests,
        currency=tracked_offer.currency,
    )
    offer_identity = OfferIdentity(
        provider_id=tracked_offer.provider,
        provider_hotel_id=provider_alias.provider_hotel_id,
        stay_query=stay_query,
        room=RoomSignature(room_label_raw=tracked_offer.room_label),
        cancellation=CancellationPolicy(policy_text_raw=tracked_offer.cancellation_policy),
    )
    stay_offer = db.scalar(
        select(HotelStayOffer).where(
            HotelStayOffer.provider == tracked_offer.provider,
            HotelStayOffer.provider_hotel_id == provider_alias.provider_hotel_id,
            HotelStayOffer.stay_query_fingerprint == stay_query.fingerprint,
            HotelStayOffer.offer_fingerprint == offer_identity.fingerprint,
        )
    )
    if stay_offer is None:
        canonical_query = {
            "check_in": stay_query.check_in.isoformat(),
            "check_out": stay_query.check_out.isoformat(),
            "occupancy": {
                "source": stay_query.occupancy.source,
                **stay_query.occupancy.fingerprint_payload(),
            },
            "currency": stay_query.currency,
        }
        stay_offer = HotelStayOffer(
            canonical_hotel_id=tracked_offer.hotel_id,
            provider=tracked_offer.provider,
            provider_hotel_id=provider_alias.provider_hotel_id,
            stay_query_fingerprint=stay_query.fingerprint,
            offer_fingerprint=offer_identity.fingerprint,
            canonical_query_json=json.dumps(canonical_query, sort_keys=True, separators=(",", ":")),
        )
        db.add(stay_offer)
        db.flush()

    watch = db.scalar(
        select(HotelUserStayWatch).where(
            HotelUserStayWatch.user_id == tracked_offer.user_id,
            HotelUserStayWatch.stay_offer_id == stay_offer.id,
        )
    )
    if watch is None:
        db.add(
            HotelUserStayWatch(
                user_id=tracked_offer.user_id,
                stay_offer_id=stay_offer.id,
                legacy_tracked_offer_id=tracked_offer.id,
            )
        )
    elif watch.legacy_tracked_offer_id != tracked_offer.id:
        raise ValueError("canonical_tracking_watch_mismatch")
    return stay_offer
