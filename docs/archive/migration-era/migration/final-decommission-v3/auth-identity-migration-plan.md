# Auth Identity & Password Migration Plan

**Authority:** 02_AUTH_SINGLE_AUTHORITY.md Phases B & C
**Date:** 2026-09-12
**Target Architecture:** Supabase Auth as Sole Authentication Authority

---

## 1. User Base Context

- **Source Database:** viru.db (SQLite)
- **Active Users in Source:** Exactly 1 user (admin/local test account)
- **PBKDF2 Hashes:** PBKDF2-HMAC-SHA256 (not direct-importable into Supabase bcrypt/Argon2 schema)

---

## 2. Identity Mapping Strategy: Explicit Remap with ID Preservation Fallback

Because existing User IDs in `users` are UUID v4 strings:
1. **Preserve IDs where supported:** When creating the user in Supabase Auth via Admin API (`supabase.auth.admin.createUser({ id: existing_uuid, email: ... })`), Supabase accepts custom UUIDs.
2. **Explicit Remap Fallback:** If Supabase assigns a fresh UUID:
   - Record in an auditable remap table: `legacy_user_id` -> `supabase_user_id`.
   - Update foreign keys transactionally across all 30 user-scoped tables:
     `flight_watch`, `hotel_watchlist_item`, `hotel_user_stay_watch`, `hotel_saved_search`, `security_activity`, etc.
   - Assert 0 orphan rows exist.

---

## 3. Password Migration: Admin Provisioning / Password Reset Flow

Given the 1-user local footprint and zero production external users:
- **Mechanism:** Forced password establishment / Admin provisioning via Supabase Auth.
- **Decommission:** Delete PBKDF2 `CryptContext`, custom JWT token issuing, and legacy `RefreshToken` tables immediately. No transitional plaintext bridge is needed in production.

