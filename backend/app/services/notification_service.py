from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import and_, asc, or_, select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.domain.vocabulary import (
    DELIVERY_STATUS_DELIVERED,
    DELIVERY_STATUS_FAILED,
    DELIVERY_STATUS_QUEUED,
    DELIVERY_STATUS_SENT,
)
from app.infrastructure.db.models import NotificationEvent

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


def _eligible_events_query(now) -> select:
    return (
        select(NotificationEvent)
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
        .limit(DEFAULT_DISPATCH_BATCH_SIZE)
    )


def dispatch_pending_events(db: Session) -> DispatchResult:
    now = utc_now_naive()
    result = DispatchResult()
    adapters: dict[str, NotificationAdapter] = {
        "in_app": InAppNotificationAdapter(),
        "email": EmailNotificationAdapter(),
    }
    rows = list(db.scalars(_eligible_events_query(now)))
    for event in rows:
        result.processed += 1
        adapter = adapters.get(event.channel)
        if not adapter:
            event.delivery_status = DELIVERY_STATUS_FAILED
            event.last_error = "unknown_channel"
            event.attempts += 1
            event.next_attempt_at = None
            result.failed += 1
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
