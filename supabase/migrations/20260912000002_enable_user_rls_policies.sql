-- Canonical security posture of viru-air (Supabase-native, see
-- docs/runbooks/runbook-supabase-native.md — source of truth):
--
--   * Row Level Security is DISABLED on every application table in `public`.
--   * `anon` and `authenticated` hold ZERO privileges on `public` (Data API
--     is effectively read/write-denied; verified live: rest/v1 responds
--     `permission denied`).
--   * The FastAPI backend, connecting as the dedicated role `viru_app`
--     through the session pooler, is the ONLY write/read path and owns all
--     authorization logic (`get_current_user`, `require_admin`).
--
-- HISTORY: this migration previously ENABLED RLS with `auth.uid()` policies
-- for `authenticated`. That posture was never applied to the hosted project
-- and contradicts the runbook; enabling RLS would break every backend insert
-- (`viru_app` is not `authenticated` and PostgREST access is not used). This
-- file is now a GUARD: re-running it (or any `supabase db push`) restores the
-- canonical posture instead of enabling RLS. Do not re-add policies here; if
-- PostgREST access is ever needed, design it deliberately with new policies
-- and update the runbook first.

-- ---------------------------------------------------------------------------
-- 1. Ensure RLS is disabled on all user-facing application tables.
--    (No-op for tables already in the canonical state.)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    t record;
BEGIN
    FOR t IN
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
          AND rowsecurity = true
    LOOP
        RAISE NOTICE 'Disabling RLS on %.%', 'public', t.tablename;
        EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', t.tablename);
    END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- 2. Revoke every table/sequence privilege from the Data API roles.
--    (Idempotent: revoking something not granted is a no-op.)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    r text;
BEGIN
    FOREACH r IN ARRAY ARRAY['anon', 'authenticated']
    LOOP
        EXECUTE format(
            'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I', r);
        EXECUTE format(
            'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %I', r);
        EXECUTE format(
            'REVOKE ALL ON SCHEMA public FROM %I', r);
        EXECUTE format(
            'REVOKE USAGE ON SCHEMA public FROM %I', r);
    END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- 3. Ensure the backend role owns the canonical grants.
--    (`viru_app` must exist; created once via the Management API/SQL editor —
--    see the runbook for the exact statements. Skipped gracefully here if the
--    role is absent so the migration also works on pristine local stacks.)
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'viru_app') THEN
        EXECUTE 'GRANT USAGE ON SCHEMA public TO viru_app';
        EXECUTE 'GRANT ALL ON ALL TABLES IN SCHEMA public TO viru_app';
        EXECUTE 'GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO viru_app';
    ELSE
        RAISE NOTICE 'Role viru_app not found; grants skipped (create it per runbook)';
    END IF;
END $$;
