# Data Authority & Schema Inventory Map

**Date:** 2026-09-12  
**Authority:** Phase 1 — `01_FREEZE_AND_BASELINE.md`  
**Target:** Single source of truth for runtime database cutover to Supabase PostgreSQL.

---

## 1. Configured Database URLs & Runtimes

- **Primary Configuration Variable:** `DB_URL` (read in `backend/app/infrastructure/db/session.py`).
- **Default Fallback:** `sqlite:///<repo-root>/viru.db` (when `DB_URL` environment variable is unset).
- **Supported Engines in Codebase:**
  - **SQLite:** Dev default, local CLI fallback, fast in-memory testing.
  - **PostgreSQL (`psycopg3` / `psycopg2`):** Supported via SQLAlchemy connection string. Pool options configured in `session.py` (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT_SECONDS`, `DB_POOL_RECYCLE_SECONDS`).
- **Cutover Target:** Supabase PostgreSQL connection string provided via `DB_URL` (direct connection for FastAPI service, pooler connection where appropriate).

---

## 2. Schema Creation & Authority Paths

1. **Alembic (Current Schema Authority):**
   - Head revision: `0062_prune_legacy_expiry_indexes`.
   - Total migration revisions: 65.
   - Command: `alembic upgrade head`.
   - Engine configuration: `backend/alembic/env.py`.
2. **Dynamic / Compatibility Schema Mutators:**
   - `backend/app/infrastructure/db/schema_compat.py`: `ensure_search_preference_columns` (alters table if legacy columns missing).
   - `backend/app/infrastructure/db/seed.py`: Seeds airport and hotel catalog data.
3. **Test Fixtures:**
   - `backend/tests/conftest.py`: Calls `Base.metadata.create_all(bind=engine)` against in-memory/temporary SQLite.
4. **Target Schema Authority After Cutover:**
   - `supabase/migrations/` exclusively. Alembic is retired.

---

## 3. Complete SQLAlchemy Tables Inventory (62 Tables)

Discovered programmatically via `Base.metadata.tables`:

### Core User & Auth (10 tables)
1. `users` (PK `id` INTEGER autoincrement, `email`, `password_hash`, `is_verified`, `is_admin`, `locale`, `timezone`, `created_at`)
2. `user_profile` (FK to `users.id`)
3. `user_session` (FK to `users.id`)
4. `refresh_token` (FK to `users.id`, self-referencing `replaced_by_token_id`)
5. `password_reset_token` (FK to `users.id`)
6. `user_preference` (FK to `users.id`)
7. `user_preference_appearance` (FK to `users.id`)
8. `user_preference_region` (FK to `users.id`)
9. `security_activity` (FK to `users.id`)
10. `idempotency_record` (FK to `users.id`)

### Flight Watchlist, Fares & Alerts (9 tables)
11. `flight_watch` (FK to `users.id`)
12. `watch_tracked_flight_leg` (FK to `flight_watch.id`)
13. `price_snapshot` (FK to `flight_watch.id`)
14. `flight_operational_snapshot` (tracked aircraft operational state)
15. `flight_operational_refresh_lock` (singleflight distributed lock)
16. `flight_provider_quota` (provider usage tracking)
17. `alert_rule` (FK to `flight_watch.id`)
18. `notification_event` (FK to `alert_rule.id`)
19. `user_notification_state` (FK to `users.id`)

### Community & Analytics (7 tables)
20. `community_price_report` (FK to `flight_watch.id`, FK to `users.id`)
21. `community_trending_snapshot` (aggregated route trends)
22. `community_trending_snapshot_route` (FK to `community_trending_snapshot.id`)
23. `quick_search_popularity_counter`
24. `quick_search_popularity_daily`
25. `ux_event` (FK to `users.id`)
26. `client_error_event` (FK to `users.id`)

### Quick Search & Caching Engine (7 tables)
27. `quick_search_cache_entry` (L2 search cache)
28. `quick_search_negative_cache_entry` (negative cache backoff)
29. `quick_search_provider_lock` (singleflight lock for route search)
30. `calendar_price_observation` (price hints across dates)
31. `flight_offer_cache_entry` (normalized offers)
32. `flight_price_observation` (FK to `flight_offer_cache_entry.id`, `quick_search_cache_entry.id`)
33. `revalidation_job` (asynchronous cache revalidation)

### Reference & General Domain (5 tables)
34. `airport` (IATA / ICAO / coordinates catalog)
35. `user_note` (FK to `users.id`)
36. `support_feedback` (user feedback, `user_id` text)
37. `suggestion` (user suggestions, `user_id` text)
38. `door_to_door_saved_location` (FK to `users.id`)

### Door-to-Door Ground Transport (3 tables)
39. `door_to_door_search_history` (FK to `users.id`, FK to `flight_watch.id`)
40. `door_to_door_saved_place` (FK to `users.id`, FK to `flight_watch.id`)
41. `door_to_door_chosen_option` (FK to `users.id`, FK to `flight_watch.id`, FK to `door_to_door_search_history.id`)

### Hotels Domain (21 tables)
42. `hotel_property` (master hotel catalog)
43. `hotel_provider_alias` (FK to `hotel_property.id`)
44. `hotel_stay_offer` (FK to `hotel_property.id`)
45. `hotel_rate_snapshot` (FK to `hotel_property.id`, `hotel_stay_offer.id`, `hotel_tracked_offer.id`, `hotel_provider_run.id`)
46. `hotel_watchlist_item` (FK to `users.id`, FK to `hotel_property.id`)
47. `hotel_comp_set` (FK to `users.id`, FK to `hotel_property.id`)
48. `hotel_comp_set_member` (FK to `hotel_comp_set.id`, FK to `hotel_property.id`)
49. `hotel_alert_rule` (FK to `users.id`, FK to `hotel_property.id`, FK to `hotel_tracked_offer.id`)
50. `hotel_provider_run` (sweep and ingest execution log)
51. `hotel_provider_latency_aggregate` (FK to `hotel_provider_run.id`)
52. `hotel_daily_metric`
53. `hotel_notification_delivery` (FK to `hotel_alert_event.id`, FK `recipient_user_id -> users.id`)
54. `hotel_sweep_lease` (distributed sweep worker lease)
55. `hotel_provider_circuit` (circuit breaker state)
56. `hotel_provider_budget` (rate limit budgets)
57. `hotel_provider_budget_reservation` (FK to `hotel_provider_budget.id`)
58. `hotel_tracked_offer` (FK to `users.id`, FK to `hotel_property.id`)
59. `hotel_tracked_offer_lifecycle_event` (FK to `hotel_tracked_offer.id`, FK to `users.id`)
60. `hotel_user_stay_watch` (FK to `users.id`, FK to `hotel_stay_offer.id`, FK to `hotel_tracked_offer.id`)
61. `hotel_saved_search` (FK to `users.id`)
62. `hotel_alert_event` (FK to `users.id`, FK to `hotel_alert_rule.id`, FK to `hotel_property.id`, FK to `hotel_provider_run.id`)

---

## 4. User ID References & Ownership Semantics

31 tables have user-scoped ownership:
- **Foreign Keys to `users.id` (29 tables):**
  `flight_watch`, `community_price_report`, `user_notification_state`, `ux_event`, `client_error_event`, `user_preference`, `user_profile`, `user_session`, `refresh_token`, `password_reset_token`, `user_preference_appearance`, `user_preference_region`, `security_activity`, `idempotency_record`, `door_to_door_saved_location`, `door_to_door_search_history`, `door_to_door_saved_place`, `door_to_door_chosen_option`, `user_note`, `hotel_watchlist_item`, `hotel_comp_set`, `hotel_alert_rule`, `hotel_notification_delivery` (`recipient_user_id`), `hotel_tracked_offer`, `hotel_tracked_offer_lifecycle_event`, `hotel_user_stay_watch`, `hotel_saved_search`, `hotel_alert_event`.
- **Soft User ID columns without formal FK (2 tables):**
  `support_feedback.user_id`, `suggestion.user_id`.

### Supabase Auth Migration Impact:
- Current `users.id` is an `INTEGER`.
- Supabase Auth `auth.users.id` is a `UUID`.
- In Phase 3, `public.users` will bridge `auth.users.id` (UUID) or retain a UUID mapping column, and RLS policies on Supabase will check `auth.uid() = user_id`.

---

## 5. Background Workers & Direct DB Consumers

The following worker scripts/processes execute queries directly:
- `backend/app/worker/notifications.py`: Polls and processes pending `notification_event` rows.
- `backend/app/worker/hotels_sweep.py`: Runs scheduled price sweeps on tracked hotels.
- `backend/app/services/fare_memory_revalidation_worker.py`: Claims and executes `revalidation_job` items.
- `backend/app/services/revalidation_worker_entrypoint.py`: Watchlist revalidation cron loop.
- `backend/app/hotels/jobs/run_hotel_sweep.py`: Hotel rate monitoring job.

