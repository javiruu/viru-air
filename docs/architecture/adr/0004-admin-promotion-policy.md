# ADR 0004: Admin Promotion Policy & RBAC via Supabase

**Date**: 2026-09-17
**Status**: Accepted

## Context
With the cutover to Supabase Auth, we must ensure that the transition from local database-driven roles to JWT-based claims does not introduce privilege escalation vulnerabilities. Specifically, we must define the singular source of truth for administrative privileges and how these privileges are granted or revoked.

During the hardening phase, it was identified that if the frontend were allowed to update arbitrary `app_metadata` or if a JWT claim inherently granted authority to self-promote, an attacker could elevate their session to an administrator.

## Decision

1. **Source of Truth for Admin State**
   - The `is_admin` flag lives exclusively inside the Supabase Auth `app_metadata.is_admin` object for each user.
   - It is encoded into the user's JWT upon sign-in or token refresh.

2. **Frontend Read-Only Access**
   - The frontend application **CANNOT** modify `app_metadata`. It relies on the read-only JWT to determine UI states (e.g., showing the admin dashboard).
   - Any attempt to update `is_admin` directly from the client using the Supabase Javascript client will be rejected by Supabase or ignored if attempted via standard `updateUser` endpoints.

3. **Backend Promotion Authority**
   - Promotion (granting admin access) and revocation are handled **exclusively** by a secured FastAPI backend route (`/admin/users/{user_id}/promote`).
   - The FastAPI backend interacts directly with the Supabase Admin API (using the Service Role Key) to mutate the `app_metadata`.
   - Only existing administrators (verified via JWT `is_admin === true` in the backend) or internal backend provisioning scripts can trigger this route.

4. **Self-Promotion Prohibition**
   - A JWT claim does **NOT** grant authority to self-promote. An admin cannot use their own token to call a generic "update my own metadata" endpoint to modify privileges.

5. **Rollback & Auditing**
   - Every promotion or revocation event is logged via OpenTelemetry and written to the `security_activity` audit table.
   - In the event of a compromised admin account, the rollback procedure involves using the Supabase Dashboard or the backend admin interface to instantly revoke the `is_admin` flag, followed by a mandatory `signOut()` broadcast or token revocation to invalidate existing JWTs before their natural expiration.

## Consequences
- **Positive**: Strict separation of concerns; the frontend only consumes state, while the backend maintains authority over privileges. Mitigates horizontal and vertical privilege escalation.
- **Negative**: Adds slight overhead to the backend, which must securely proxy requests to the Supabase Admin API rather than relying purely on Postgres RLS for role management.
