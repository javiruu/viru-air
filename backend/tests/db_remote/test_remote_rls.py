import os
import pytest
from pathlib import Path

TEST_DB_URL = os.getenv("TEST_SUPABASE_DB_URL") or os.getenv("DB_URL")
SUPABASE_PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "")
SUPABASE_ENV = os.getenv("VIRU_SUPABASE_ENV", "dev")

USER_SCOPED_TABLES = [
    "client_error_event", "community_price_report", "door_to_door_chosen_option",
    "door_to_door_saved_location", "door_to_door_saved_place", "door_to_door_search_history",
    "flight_watch", "hotel_alert_event", "hotel_alert_rule", "hotel_comp_set",
    "hotel_notification_delivery", "hotel_saved_search", "hotel_tracked_offer",
    "hotel_tracked_offer_lifecycle_event", "hotel_user_stay_watch", "hotel_watchlist_item",
    "idempotency_record", "password_reset_token", "refresh_token", "security_activity",
    "suggestion", "support_feedback", "user_note", "user_notification_state",
    "user_preference", "user_preference_appearance", "user_preference_region",
    "user_profile", "user_session", "ux_event"
]


def test_production_safety_guardrail():
    """Verify tests strictly refuse to run destructive actions against production."""
    if SUPABASE_ENV.lower() in ("prod", "production"):
        pytest.fail("Safety guardrail: tests must NEVER target production Supabase environment.")


@pytest.mark.skipif(not TEST_DB_URL or not TEST_DB_URL.startswith("postgres"), reason="SKIPPED_NO_SECRETS: Remote hosted Supabase credentials not configured in current environment")
def test_remote_supabase_rls_enabled_across_all_user_tables():
    """Validates that RLS is active across all 30 user-scoped tables in the remote database."""
    from sqlalchemy import create_engine, text
    engine = create_engine(TEST_DB_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';"))
        rls_map = {row[0]: row[1] for row in result.fetchall()}
        for table in USER_SCOPED_TABLES:
            assert rls_map.get(table) is True, f"RLS must be enabled on user-scoped table: {table}"
