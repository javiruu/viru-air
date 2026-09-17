-- Remote Schema Fingerprint & RLS Audit Query
-- Validates that all 30 user-scoped tables have Row Level Security enabled in PostgreSQL.

SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
