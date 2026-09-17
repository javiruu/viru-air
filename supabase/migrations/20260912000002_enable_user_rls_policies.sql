-- Enable Row Level Security (RLS) on all user-scoped tables
-- Policy: Authenticated users can only access their own data via auth.uid()
-- Backend services / workers using service_role have full access

ALTER TABLE public.client_error_event ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own client_error_event" ON public.client_error_event;
CREATE POLICY "Users own client_error_event" ON public.client_error_event
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.community_price_report ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own community_price_report" ON public.community_price_report;
CREATE POLICY "Users own community_price_report" ON public.community_price_report
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.door_to_door_chosen_option ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own door_to_door_chosen_option" ON public.door_to_door_chosen_option;
CREATE POLICY "Users own door_to_door_chosen_option" ON public.door_to_door_chosen_option
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.door_to_door_saved_location ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own door_to_door_saved_location" ON public.door_to_door_saved_location;
CREATE POLICY "Users own door_to_door_saved_location" ON public.door_to_door_saved_location
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.door_to_door_saved_place ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own door_to_door_saved_place" ON public.door_to_door_saved_place;
CREATE POLICY "Users own door_to_door_saved_place" ON public.door_to_door_saved_place
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.door_to_door_search_history ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own door_to_door_search_history" ON public.door_to_door_search_history;
CREATE POLICY "Users own door_to_door_search_history" ON public.door_to_door_search_history
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.flight_watch ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own flight_watch" ON public.flight_watch;
CREATE POLICY "Users own flight_watch" ON public.flight_watch
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.hotel_alert_event ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own hotel_alert_event" ON public.hotel_alert_event;
CREATE POLICY "Users own hotel_alert_event" ON public.hotel_alert_event
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.hotel_alert_rule ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own hotel_alert_rule" ON public.hotel_alert_rule;
CREATE POLICY "Users own hotel_alert_rule" ON public.hotel_alert_rule
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.hotel_comp_set ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own hotel_comp_set" ON public.hotel_comp_set;
CREATE POLICY "Users own hotel_comp_set" ON public.hotel_comp_set
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.hotel_notification_delivery ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own hotel_notification_delivery" ON public.hotel_notification_delivery;
CREATE POLICY "Users own hotel_notification_delivery" ON public.hotel_notification_delivery
    FOR ALL TO authenticated
    USING ((auth.uid())::text = recipient_user_id::text)
    WITH CHECK ((auth.uid())::text = recipient_user_id::text);

ALTER TABLE public.hotel_saved_search ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own hotel_saved_search" ON public.hotel_saved_search;
CREATE POLICY "Users own hotel_saved_search" ON public.hotel_saved_search
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.hotel_tracked_offer ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own hotel_tracked_offer" ON public.hotel_tracked_offer;
CREATE POLICY "Users own hotel_tracked_offer" ON public.hotel_tracked_offer
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.hotel_tracked_offer_lifecycle_event ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own hotel_tracked_offer_lifecycle_event" ON public.hotel_tracked_offer_lifecycle_event;
CREATE POLICY "Users own hotel_tracked_offer_lifecycle_event" ON public.hotel_tracked_offer_lifecycle_event
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.hotel_user_stay_watch ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own hotel_user_stay_watch" ON public.hotel_user_stay_watch;
CREATE POLICY "Users own hotel_user_stay_watch" ON public.hotel_user_stay_watch
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.hotel_watchlist_item ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own hotel_watchlist_item" ON public.hotel_watchlist_item;
CREATE POLICY "Users own hotel_watchlist_item" ON public.hotel_watchlist_item
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.idempotency_record ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own idempotency_record" ON public.idempotency_record;
CREATE POLICY "Users own idempotency_record" ON public.idempotency_record
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.password_reset_token ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own password_reset_token" ON public.password_reset_token;
CREATE POLICY "Users own password_reset_token" ON public.password_reset_token
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.refresh_token ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own refresh_token" ON public.refresh_token;
CREATE POLICY "Users own refresh_token" ON public.refresh_token
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.security_activity ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own security_activity" ON public.security_activity;
CREATE POLICY "Users own security_activity" ON public.security_activity
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.suggestion ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own suggestion" ON public.suggestion;
CREATE POLICY "Users own suggestion" ON public.suggestion
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.support_feedback ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own support_feedback" ON public.support_feedback;
CREATE POLICY "Users own support_feedback" ON public.support_feedback
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.user_note ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own user_note" ON public.user_note;
CREATE POLICY "Users own user_note" ON public.user_note
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.user_notification_state ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own user_notification_state" ON public.user_notification_state;
CREATE POLICY "Users own user_notification_state" ON public.user_notification_state
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.user_preference ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own user_preference" ON public.user_preference;
CREATE POLICY "Users own user_preference" ON public.user_preference
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.user_preference_appearance ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own user_preference_appearance" ON public.user_preference_appearance;
CREATE POLICY "Users own user_preference_appearance" ON public.user_preference_appearance
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.user_preference_region ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own user_preference_region" ON public.user_preference_region;
CREATE POLICY "Users own user_preference_region" ON public.user_preference_region
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.user_profile ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own user_profile" ON public.user_profile;
CREATE POLICY "Users own user_profile" ON public.user_profile
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.user_session ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own user_session" ON public.user_session;
CREATE POLICY "Users own user_session" ON public.user_session
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);

ALTER TABLE public.ux_event ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users own ux_event" ON public.ux_event;
CREATE POLICY "Users own ux_event" ON public.ux_event
    FOR ALL TO authenticated
    USING ((auth.uid())::text = user_id::text)
    WITH CHECK ((auth.uid())::text = user_id::text);
