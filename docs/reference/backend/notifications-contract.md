# Notifications contract

**Estado:** vivo
**Ultima revision:** 2026-07-30
**Fuente de verdad:** si
**Area:** backend

## Scope

The notifications inbox is a private, authenticated API under `/api/v1/notifications`. It aggregates existing event sources and stores per-user read state without mutating the source events.

## Endpoints

### `GET /api/v1/notifications`

Returns the current user's notification inbox.

Response shape:

```json
{
  "items": [
    {
      "id": "alert_event:123",
      "source_type": "alert_event",
      "source_id": 123,
      "category": "price",
      "title": "Movimiento de precio detectado",
      "body": "Precio bajo: 39.00 EUR (umbral 45.00).",
      "created_at": "2026-07-03T10:00:00Z",
      "read_at": null,
      "action_href": "/notifications?view=rules",
      "route_label": "MAD -> DUB",
      "tone": "success"
    }
  ],
  "summary": {
    "total": 1,
    "unread": 1,
    "price": 1,
    "security": 0,
    "digest": 0,
    "worker": 0
  }
}
```

`category` is one of `price`, `security`, `digest`, or `worker`.

### `GET /api/v1/notifications/summary`

Returns only the aggregate counters for the current user's inbox. The private navigation uses this endpoint for the unread badge so it can surface pending signals without loading the full inbox UI.

Response shape:

```json
{
  "total": 4,
  "unread": 2,
  "price": 2,
  "security": 1,
  "digest": 1,
  "worker": 0
}
```

### `POST /api/v1/notifications/{source_type}/{source_id}/read`

Marks one notification source as read for the current user.

Allowed `source_type` values:

- `alert_event`
- `hotel_alert_event`
- `security_activity`

The endpoint validates that the source belongs to the authenticated user before writing read state.

### `POST /api/v1/notifications/read-all`

Marks all currently listed inbox items as read for the current user.

## Persistence

Read state is stored in `user_notification_state`:

- `user_id`
- `source_type`
- `source_id`
- `read_at`

The unique key is `(user_id, source_type, source_id)`. Source rows remain immutable, so future aggregations can safely re-read historical event data.

## Source mapping

`notification_event` rows are owned through `alert_rule -> flight_watch -> user_id` and mapped as:

- `worker` when delivery failed or the event marks a revalidation failure;
- `digest` when the event is digest/grouped;
- `price` otherwise.

`hotel_alert_event` rows are owned through either `hotel_alert_rule.user_id` or a `hotel_tracked_offer` for the same hotel/user. They are mapped as `price`, with favorable hotel movement using `success`, increases/parity breaks using `warning`, and neutral radar changes using `info`.

`security_activity` rows are mapped as `security`.

The inbox bounds returned data to keep the screen usable and avoid a security-activity flood dominating price/workers signals.

## Lifecycle cleanup

Account deletion removes notification read states for the user after deleting the user's flight, hotel, and security sources. Admin watch deletion also removes read states tied to deleted flight notification events.
