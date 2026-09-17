# ADR 0003 — Supabase Migration Authority & Alembic Retirement

**Status:** Executed / Cutover Complete
**Date:** 2026-09-12
**Deciders:** Core Engineering Team
**Authority:** 01_DATABASE_SINGLE_AUTHORITY.md (viru-final-decommission-v3)

---

## Context

Viru historically used Alembic for incremental database migrations alongside SQLite in local development and test environments. Having two concurrent schema migration systems (Alembic and Supabase CLI migrations) introduced severe risks of schema drift, unmanaged RLS policies, and environment divergence.

## Decision

1. **Sole DDL Authority:** `supabase/migrations/` is the single, exclusive source of truth for all database schema definition and DDL operations across all environments.
2. **Alembic Decommissioning:** Alembic has been permanently retired and deleted from the active tree (`backend/alembic.ini`, `backend/alembic/`, `backend/app/infrastructure/db/alembic_audit.py`, and `pyproject.toml` dependency removed). Git history preserves historical revisions.
3. **Canonical Baseline:** `supabase/migrations/20260912000001_canonical_baseline_schema.sql` establishes the complete 62 application tables, followed by `20260912000002_enable_user_rls_policies.sql` establishing user-level RLS policies.
4. **Role of SQLAlchemy:** SQLAlchemy remains the active backend ORM, query builder, and model layer for FastAPI. DDL is never executed at runtime.
5. **SQLite Retirement:** SQLite is completely removed from runtime paths and configuration.

## Status and Execution Proof

- Alembic runtime/deploy references: 0
- SQLite runtime references: 0
- Schema equivalence: 62/62 tables verified
- Data reconciliation: 100% exact parity across populated tables
