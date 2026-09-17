-- Seed data for local testing (Non-PII synthetic data)
-- Follows: viru-modernization-codex/08_SUPABASE.md

INSERT INTO public.flight_watch (id, user_id, origin_iata, destination_iata, travel_date_local, target_price, status)
VALUES
    ('00000000-0000-0000-0000-000000000001', 'synthetic-user-1', 'MAD', 'BCN', '2026-10-15', 45.00, 'active'),
    ('00000000-0000-0000-0000-000000000002', 'synthetic-user-1', 'MAD', 'PAR', '2026-10-20', 60.00, 'active'),
    ('00000000-0000-0000-0000-000000000003', 'synthetic-user-2', 'BCN', 'LON', '2026-11-05', 55.00, 'active')
ON CONFLICT (user_id, origin_iata, destination_iata, travel_date_local) DO NOTHING;

