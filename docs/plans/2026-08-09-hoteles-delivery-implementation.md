# Hotel Delivery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Persist and process hotel alert delivery independently from flight notifications, with verified in-app materialization and no external email.

**Architecture:** Add a `HotelNotificationDelivery` ledger linked to an owned `HotelAlertEvent` and recipient user. Generate one idempotent in-app delivery intent for newly created events in a sweep transaction, then process queued rows in the existing notification worker through a hotel-specific dispatcher. Keep the public inbox sourced from `HotelAlertEvent`; delivery state remains internal until a later contract extension.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest, existing Python worker/backoff utilities.

---

### Task 1: Add the delivery ledger model and migration

**Files:**
- Modify: `backend/app/infrastructure/db/models.py`
- Create: `backend/alembic/versions/0050_hotel_notification_delivery.py`
- Test: `backend/tests/unit/test_hotel_provider_infrastructure_migration.py`

Add `HotelNotificationDelivery` with source event, recipient, channel, template version, idempotency key, status, attempts, next attempt, last error, delivered/created/updated timestamps. Add unique idempotency index and indexes for queue and recipient. Use nullable-safe foreign keys where legacy migration compatibility requires it, but new writes require ownership.

Run the migration audit/roundtrip test before implementation of services.

### Task 2: Add domain/service helpers for safe intent creation

**Files:**
- Modify: `backend/app/services/hotels_service.py`
- Test: `backend/tests/unit/test_hotels_delivery.py`

Implement a helper that accepts only a user-owned `HotelAlertEvent`, validates `event.user_id` and rule ownership, uses `provider_run_id` as the run linkage, derives a stable idempotency hash from event/user/channel/template version, and inserts or returns the existing row. It must reject legacy orphan events and never use hotel ID for ownership.

Write tests for owner success, cross-user rejection, legacy rule-owned compatibility, orphan rejection, and idempotent replay.

### Task 3: Generate intents atomically from hotel sweeps

**Files:**
- Modify: `backend/app/services/hotels_service.py`
- Test: `backend/tests/unit/test_hotels_delivery.py`

After `evaluate_hotel_alerts` and tracked-offer event creation, create in-app intents for events from the current run before the run commit. Avoid creating duplicate intents if a run is replayed. Keep global sweeps free of browser client intents.

Cover multiple users in one run and assert each delivery recipient matches its event owner.

### Task 4: Process hotel delivery in the notification worker

**Files:**
- Modify: `backend/app/services/notification_service.py`
- Modify: `backend/app/worker/notifications.py`
- Test: `backend/tests/integration/test_notification_worker.py`

Add a hotel-specific dispatcher for queued in-app rows. Select only due rows, increment attempts, mark local in-app delivery as delivered, and preserve/advance retry metadata on failures. Do not alter the existing flight `NotificationEvent` query or adapters. Make the worker cycle include hotel counts without changing existing result fields incompatibly.

Test successful delivery, due/future scheduling, idempotent rerun, ownership isolation, and coexistence with flight notifications.

### Task 5: Update H28/H41/roadmap evidence

**Files:**
- Modify: `docs/reference/backend/hoteles-delivery-retries-preferences-h28.md`
- Modify: `docs/reference/backend/hoteles-observability-e2e-h41.md`
- Modify: `docs/plans/2026-08-04-hoteles-master-roadmap.md`

Record that hotel in-app delivery is implemented and bounded, email/push remain inactive, public inbox remains event-sourced, and global sweep runs have no browser intent. Document exact tests and remaining gaps.

### Task 6: Validate and review

Run:

```bash
cd backend
python -m pytest tests/unit/test_hotels_delivery.py tests/integration/test_notification_inbox.py tests/integration/test_notification_worker.py tests/integration/test_hotels_api_flow.py tests/unit/test_hotel_provider_infrastructure_migration.py -q
python -m ruff check app/services/hotels_service.py app/services/notification_service.py app/worker/notifications.py tests/unit/test_hotels_delivery.py tests/integration/test_notification_worker.py
python -m py_compile app/services/hotels_service.py app/services/notification_service.py app/worker/notifications.py
cd ..
git diff --check
```

Run an independent blocker-only review over the model, migration, services, worker and tests before closing the increment.
