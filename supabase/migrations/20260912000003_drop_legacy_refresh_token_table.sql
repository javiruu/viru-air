-- Supabase Migration: Drop legacy refresh token table
DROP TABLE IF EXISTS refresh_token CASCADE;
