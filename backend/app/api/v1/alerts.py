from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse

from app.core.idempotency import replay_if_exists, request_hash, store_response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import AlertEvaluateIn, AlertRuleIn, AlertRuleUpdateIn
from app.infrastructure.db.models import AlertRule, FlightWatch, User
from app.infrastructure.db.session import get_db
from app.services.alert_service import (
    create_rule,
    delete_rule,
    evaluate_rules_for_watch,
    list_events,
    list_rules,
    update_rule,
)

router = APIRouter()


@router.post("/rules")
def add_rule(
    payload: AlertRuleIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    req_hash = request_hash(payload.model_dump(mode="json"))
    endpoint = "POST:/api/v1/alerts/rules"
    replay = replay_if_exists(
        db,
        user_id=current_user.id,
        endpoint=endpoint,
        idempotency_key=idempotency_key,
        req_hash=req_hash,
    )
    if replay:
        status_code, body = replay
        response = JSONResponse(status_code=status_code, content=body)
        response.headers["x-idempotency-replayed"] = "true"
        return response

    watch = db.get(FlightWatch, payload.watch_id)
    if not watch:
        raise HTTPException(status_code=404, detail="watch_not_found")
    if watch.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="not_allowed")
    rule = create_rule(db, payload)
    body = {
        "id": rule.id,
        "watch_id": rule.watch_id,
        "rule_type": rule.rule_type,
        "threshold_value": float(rule.threshold_value) if rule.threshold_value is not None else None,
        "notify_on_every_change": rule.notify_on_every_change,
        "cooldown_minutes": rule.cooldown_minutes,
        "enabled": rule.enabled,
    }
    store_response(
        db,
        user_id=current_user.id,
        endpoint=endpoint,
        idempotency_key=idempotency_key,
        req_hash=req_hash,
        response_status=200,
        response_body=body,
    )
    return body


@router.get("/rules")
def get_rules(
    watch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    watch = db.get(FlightWatch, watch_id)
    if not watch:
        raise HTTPException(status_code=404, detail="watch_not_found")
    if watch.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="not_allowed")
    rows = list_rules(db, watch_id)
    return [
        {
            "id": r.id,
            "watch_id": r.watch_id,
            "rule_type": r.rule_type,
            "threshold_value": r.threshold_value,
            "notify_on_every_change": r.notify_on_every_change,
            "cooldown_minutes": r.cooldown_minutes,
            "enabled": r.enabled,
        }
        for r in rows
    ]


@router.put("/rules/{rule_id}")
def update_rule_handler(
    rule_id: str,
    payload: AlertRuleUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    rule = db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="rule_not_found")
    watch = db.get(FlightWatch, rule.watch_id)
    if not watch or watch.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="not_allowed")
    updated = update_rule(db, rule, payload)
    return {
        "id": updated.id,
        "watch_id": updated.watch_id,
        "rule_type": updated.rule_type,
        "threshold_value": updated.threshold_value,
        "notify_on_every_change": updated.notify_on_every_change,
        "cooldown_minutes": updated.cooldown_minutes,
        "enabled": updated.enabled,
    }


@router.delete("/rules/{rule_id}")
def delete_rule_handler(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    rule = db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="rule_not_found")
    watch = db.get(FlightWatch, rule.watch_id)
    if not watch or watch.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="not_allowed")
    delete_rule(db, rule)
    return {"status": "ok"}


@router.post("/evaluate")
def evaluate_rules(
    payload: AlertEvaluateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    watch = db.get(FlightWatch, payload.watch_id)
    if not watch or watch.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="watch_not_found")
    events = evaluate_rules_for_watch(db, payload.watch_id)
    return {
        "status": "ok",
        "created": len(events),
        "events": [
            {
                "id": e.id,
                "rule_id": e.rule_id,
                "channel": e.channel,
                "delivery_status": e.delivery_status,
                "message": e.message,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
    }


@router.get("/events")
def get_events(
    watch_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    rows = list_events(db, current_user.id, watch_id=watch_id, limit=limit)
    return [
        {
            "id": event.id,
            "rule_id": rule.id,
            "watch_id": watch.id,
            "origin_iata": watch.origin_iata,
            "destination_iata": watch.destination_iata,
            "travel_date_local": str(watch.travel_date_local),
            "channel": event.channel,
            "delivery_status": event.delivery_status,
            "message": event.message,
            "created_at": event.created_at.isoformat(),
        }
        for event, rule, watch in rows
    ]
