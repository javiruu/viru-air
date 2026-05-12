from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, asc, or_, select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.domain.vocabulary import (
    DELIVERY_STATUS_DELIVERED,
    DELIVERY_STATUS_FAILED,
    DELIVERY_STATUS_QUEUED,
    DELIVERY_STATUS_SENT,
)
from app.infrastructure.db.models import AlertRule, FlightWatch, NotificationEvent, User, UserPreference

DEFAULT_DISPATCH_BATCH_SIZE = int(os.getenv("NOTIFICATION_DISPATCH_BATCH_SIZE", "25"))
DEFAULT_MAX_ATTEMPTS = int(os.getenv("NOTIFICATION_MAX_ATTEMPTS", "3"))


@dataclass
class DispatchResult:
    processed: int = 0
    delivered: int = 0
    failed: int = 0
    retried: int = 0
    skipped: int = 0


class NotificationAdapter:
    channel: str

    def send(self, event: NotificationEvent) -> tuple[bool, str | None]:
        raise NotImplementedError


class InAppNotificationAdapter(NotificationAdapter):
    channel = "in_app"

    def send(self, event: NotificationEvent) -> tuple[bool, str | None]:
        return True, None


class EmailNotificationAdapter(NotificationAdapter):
    channel = "email"

    def send(self, event: NotificationEvent) -> tuple[bool, str | None]:
        # Stub: intentionally avoids external email delivery in this scope.
        should_fail = event.message.lower().startswith("force_fail")
        if should_fail:
            return False, "email_stub_forced_failure"
        return True, None


def _next_attempt_delay(attempts: int) -> timedelta:
    # Small bounded backoff for manual dispatcher usage.
    minutes = min(30, 2 ** max(0, attempts - 1))
    return timedelta(minutes=minutes)


def _eligible_events_query(now, *, limit: int) -> select:
    return (
        select(NotificationEvent, User, UserPreference)
        .join(AlertRule, NotificationEvent.rule_id == AlertRule.id)
        .join(FlightWatch, AlertRule.watch_id == FlightWatch.id)
        .join(User, FlightWatch.user_id == User.id)
        .outerjoin(UserPreference, UserPreference.user_id == User.id)
        .where(
            and_(
                NotificationEvent.attempts < DEFAULT_MAX_ATTEMPTS,
                or_(
                    NotificationEvent.delivery_status == DELIVERY_STATUS_QUEUED,
                    and_(
                        NotificationEvent.delivery_status == DELIVERY_STATUS_FAILED,
                        NotificationEvent.next_attempt_at.is_not(None),
                        NotificationEvent.next_attempt_at <= now,
                    ),
                ),
            )
        )
        .order_by(asc(NotificationEvent.created_at), asc(NotificationEvent.id))
        .limit(limit)
    )


def _parse_hhmm(value: str | None) -> tuple[int, int] | None:
    if not value or ":" not in value:
        return None
    hour, minute = value.split(":", 1)
    return int(hour), int(minute)


def _quiet_hours_end(
    now_utc_naive: datetime,
    timezone_name: str,
    start_hhmm: str | None,
    end_hhmm: str | None,
) -> datetime | None:
    start = _parse_hhmm(start_hhmm)
    end = _parse_hhmm(end_hhmm)
    if not start or not end:
        return None
    now_local = now_utc_naive.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(timezone_name))
    start_local = now_local.replace(hour=start[0], minute=start[1], second=0, microsecond=0)
    end_local = now_local.replace(hour=end[0], minute=end[1], second=0, microsecond=0)

    if start_local < end_local:
        in_quiet = start_local <= now_local < end_local
        if not in_quiet:
            return None
        return end_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    in_quiet = now_local >= start_local or now_local < end_local
    if not in_quiet:
        return None
    if now_local >= start_local:
        end_local = end_local + timedelta(days=1)
    return end_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def dispatch_pending_events(db: Session, *, limit: int | None = None) -> DispatchResult:
    now = utc_now_naive()
    result = DispatchResult()
    batch_limit = limit if limit is not None else DEFAULT_DISPATCH_BATCH_SIZE
    adapters: dict[str, NotificationAdapter] = {
        "in_app": InAppNotificationAdapter(),
        "email": EmailNotificationAdapter(),
    }
    rows = list(db.execute(_eligible_events_query(now, limit=batch_limit)).all())
    for event, user, preference in rows:
        result.processed += 1
        adapter = adapters.get(event.channel)
        if not adapter:
            event.delivery_status = DELIVERY_STATUS_FAILED
            event.last_error = "unknown_channel"
            event.attempts += 1
            event.next_attempt_at = None
            result.failed += 1
            continue

        timezone_name = (
            (preference.quiet_hours_timezone if preference else None)
            or user.timezone
            or "Europe/Madrid"
        )
        quiet_until = _quiet_hours_end(
            now,
            timezone_name=timezone_name,
            start_hhmm=preference.quiet_hours_start if preference else None,
            end_hhmm=preference.quiet_hours_end if preference else None,
        )
        # Design decision: in-app remains deliverable for internal traceability.
        if (
            event.channel == "email"
            and preference
            and preference.quiet_hours_enabled
            and quiet_until is not None
        ):
            event.delivery_status = DELIVERY_STATUS_QUEUED
            event.next_attempt_at = quiet_until
            event.last_error = "quiet_hours_active"
            result.retried += 1
            continue

        event.attempts += 1
        ok, error = adapter.send(event)
        if ok:
            if event.channel == "email":
                event.delivery_status = DELIVERY_STATUS_SENT
            else:
                event.delivery_status = DELIVERY_STATUS_DELIVERED
            event.delivered_at = now
            event.next_attempt_at = None
            event.last_error = None
            result.delivered += 1
            continue

        event.delivery_status = DELIVERY_STATUS_FAILED
        event.last_error = (error or "dispatch_failed")[:500]
        if event.attempts >= DEFAULT_MAX_ATTEMPTS:
            event.next_attempt_at = None
            result.failed += 1
        else:
            event.next_attempt_at = now + _next_attempt_delay(event.attempts)
            result.retried += 1

    db.commit()

    stuck_rows = list(
        db.scalars(
            select(NotificationEvent).where(
                NotificationEvent.delivery_status == DELIVERY_STATUS_FAILED,
                NotificationEvent.attempts >= DEFAULT_MAX_ATTEMPTS,
            )
        )
    )
    result.skipped = len(stuck_rows)
    return result
